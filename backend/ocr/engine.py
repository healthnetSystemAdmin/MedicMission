import os
import re
import json
import cv2
import numpy as np
import traceback

# --- CRITICAL RPI SEGFAULT HARDENING ---
# These must be set before ANY other imports
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ['MKL_THREADING_LAYER'] = 'GNU'
os.environ['KMP_BLOCKTIME'] = '0'
os.environ['LD_BIND_NOW'] = '1'

# Paddle-specific memory management for ARM
os.environ['FLAGS_allocator_strategy'] = 'naive_best_fit'
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_mkldnn'] = '0'

try:
    import paddle
    # Explicitly set device to CPU before loading OCR
    paddle.set_device('cpu')
    # Disable static mode if needed (common fix for RPi)
    if hasattr(paddle, 'disable_static'):
        paddle.disable_static()
except Exception as e:
    print(f"Warning: Could not set paddle device flags: {e}")

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("!!! PaddleOCR library not found !!!")

class OCRProcessor:
    def __init__(self):
        print("--- Initializing PaddleOCR (Hardened RPi Mode) ---")
        self.ocr = None
        
        try:
            # Try minimal initialization
            try:
                self.ocr = PaddleOCR(lang='en', use_angle_cls=False, show_log=False)
            except (ValueError, TypeError):
                # Fallback for older or specific ARM versions that don't like 'lang' or 'show_log'
                self.ocr = PaddleOCR() 
            
            if self.ocr:
                print("--- Engine Initialized. Running Warmup... ---")
                # Warmup: Run a tiny inference on a blank image to 'lock' memory
                # This catches SegFaults at startup instead of during usage
                blank_img = np.zeros((100, 100, 3), dtype=np.uint8)
                self.ocr.ocr(blank_img, cls=False)
                print("--- PaddleOCR Engine Ready & Warmed Up ---")
        except Exception as e:
            print("!!! OCR INITIALIZATION/WARMUP FAILED !!!")
            traceback.print_exc()
            self.ocr = None

    def process_image(self, img_path):
        if self.ocr is None:
            raise RuntimeError("OCR Engine not ready. Check startup logs.")
            
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found at {img_path}")

        try:
            # IMPORTANT: Load image with OpenCV first and pass the array.
            # Passing the path string to Paddle sometimes triggers 
            # SegFaults in the internal C++ file reader on ARM.
            img = cv2.imread(img_path)
            if img is None:
                raise ValueError("Could not decode image with OpenCV")

            # Inference using the numpy array
            try:
                result = self.ocr.ocr(img, cls=False)
            except Exception:
                # Last resort bare call
                result = self.ocr.ocr(img)
                
        except Exception as e:
            print(f"Inference Crash: {e}")
            traceback.print_exc()
            raise RuntimeError(f"PaddleOCR Inference Failed: {str(e)}")
        
        lines = []
        if result and result[0]:
            for line in result[0]:
                lines.append({
                    "text": line[1][0],
                    "confidence": line[1][1]
                })

        extracted = self.parse_fields(lines)
        
        return {
            "fields": extracted,
            "image": {
                "stored_filename": os.path.basename(img_path),
                "preview_url": os.path.basename(img_path)
            },
            "debug": {
                "ocr_engine": "paddleocr-rpi-hardened",
                "notes": f"Detected {len(lines)} text blocks"
            }
        }

    def parse_fields(self, lines):
        """Heuristic parser for PhilHealth cards"""
        data = {
            "philhealth_no": {"value": "", "confidence": 0.0},
            "last_name": {"value": "", "confidence": 0.0},
            "first_name": {"value": "", "confidence": 0.0},
            "middle_name": {"value": "", "confidence": 0.0},
            "birth_date": {"value": "", "confidence": 0.0},
            "sex": {"value": "", "confidence": 0.0},
            "address": {"value": "", "confidence": 0.0},
        }

        all_text = " ".join([l['text'] for l in lines])
        
        id_pattern = r'(\d{2}-\d{9}-\d{1})'
        id_match = re.search(id_pattern, all_text)
        if id_match:
            data['philhealth_no'] = {"value": id_match.group(1), "confidence": 0.95}

        if re.search(r'\b(MALE|M)\b', all_text, re.I):
            data['sex'] = {"value": "Male", "confidence": 0.9}
        elif re.search(r'\b(FEMALE|F)\b', all_text, re.I):
            data['sex'] = {"value": "Female", "confidence": 0.9}

        for i, line in enumerate(lines):
            txt = line['text'].upper()
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})|(\d{2}-\d{2}-\d{4})', txt)
            if date_match and data['birth_date']['value'] == "":
                data['birth_date'] = {"value": date_match.group(0), "confidence": line['confidence']}

            if any(k in txt for k in ["LAST NAME", "SURNAME"]):
                if i + 1 < len(lines):
                    data['last_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}
            
            if any(k in txt for k in ["GIVEN NAME", "FIRST NAME"]):
                if i + 1 < len(lines):
                    data['first_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}

        if not data['last_name']['value']:
            candidates = [l for l in lines if len(l['text']) > 3 and not any(x in l['text'].upper() for x in ["PHILHEALTH", "REPUBLIC", "ID", "NUMBER"])]
            if len(candidates) >= 2:
                data['last_name'] = {"value": candidates[0]['text'].title(), "confidence": candidates[0]['confidence'] * 0.7}
                data['first_name'] = {"value": candidates[1]['text'].title(), "confidence": candidates[1]['confidence'] * 0.7}

        return data
