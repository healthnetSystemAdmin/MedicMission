import os
import re
import json
import cv2
import numpy as np
import traceback
import time

# --- CRITICAL RPI SEGFAULT HARDENING ---
# These must be set before ANY other imports to lock the environment
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
    # Force CPU device immediately
    paddle.set_device('cpu')
    if hasattr(paddle, 'disable_static'):
        paddle.disable_static()
except Exception as e:
    print(f"Warning: Paddle device config failed: {e}")

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("!!! PaddleOCR library not found !!!")

class OCRProcessor:
    def __init__(self):
        print("--- Preparing Hardened OCR Engine (Adaptive Mode) ---")
        self.ocr = None
        # We delay initialization slightly to let the system settle after boot
        time.sleep(1)
        self._initialize_engine()

    def _initialize_engine(self):
        """
        Helper to try and load the most stable OCR model.
        The constructor arguments vary wildly between PaddleOCR versions.
        """
        # Strategy 1: Attempt standard mobile-optimized config
        try:
            print("Attempting standard Mobile-V4 initialization...")
            self.ocr = PaddleOCR(
                lang='en',
                ocr_version='PP-OCRv4',
                use_angle_cls=False,
                use_gpu=False,
                enable_mkldnn=False,
                det_limit_side_len=736,
                det_limit_type='max'
            )
            print("--- PP-OCRv4 Engine Ready ---")
            return
        except Exception as e:
            print(f"Mobile-V4 init failed: {e}")

        # Strategy 2: Absolute barebones
        # Many newer versions (3.0+) handle 'use_gpu' and 'show_log' via internal configs
        try:
            print("Attempting barebones initialization (No arguments)...")
            self.ocr = PaddleOCR()
            print("--- Barebones Engine Ready ---")
            return
        except Exception as e:
            print(f"Barebones init failed: {e}")
            self.ocr = None
            traceback.print_exc()

    def process_image(self, img_path):
        # Lazy check if init failed previously
        if self.ocr is None:
            self._initialize_engine()
            
        if self.ocr is None:
            raise RuntimeError("OCR Engine could not be initialized. Please check Pi console logs.")
            
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found at {img_path}")

        try:
            # Load image with OpenCV to ensure it's a valid numpy array before reaching Paddle
            img = cv2.imread(img_path)
            if img is None:
                raise ValueError("OpenCV failed to decode image")

            # Run inference on the numpy array
            # Note: We do NOT pass any extra args (like cls=False) to avoid version mismatches
            result = self.ocr.ocr(img)
                
        except Exception as e:
            print(f"Inference Crash: {e}")
            traceback.print_exc()
            raise RuntimeError(f"PaddleOCR Inference Failed: {str(e)}")
        
        lines = []
        # Result structure can be [ [[coords], [text, conf]], ... ] or None
        if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                if len(line) > 1 and len(line[1]) > 1:
                    lines.append({
                        "text": str(line[1][0]),
                        "confidence": float(line[1][1])
                    })

        extracted = self.parse_fields(lines)
        
        return {
            "fields": extracted,
            "image": {
                "stored_filename": os.path.basename(img_path),
                "preview_url": os.path.basename(img_path)
            },
            "debug": {
                "ocr_engine": "paddleocr-adaptive",
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

        if not lines:
            return data

        all_text = " ".join([l['text'] for l in lines])
        
        # ID Number Pattern
        id_pattern = r'(\d{2}-\d{9}-\d{1})'
        id_match = re.search(id_pattern, all_text)
        if id_match:
            data['philhealth_no'] = {"value": id_match.group(1), "confidence": 0.95}

        # Sex Heuristic
        if re.search(r'\b(MALE|M)\b', all_text, re.I):
            data['sex'] = {"value": "Male", "confidence": 0.9}
        elif re.search(r'\b(FEMALE|F)\b', all_text, re.I):
            data['sex'] = {"value": "Female", "confidence": 0.9}

        # Field Extraction
        for i, line in enumerate(lines):
            txt = line['text'].upper()
            
            # Date of Birth
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})|(\d{2}-\d{2}-\d{4})', txt)
            if date_match and data['birth_date']['value'] == "":
                data['birth_date'] = {"value": date_match.group(0), "confidence": line['confidence']}

            # Name matching
            if any(k in txt for k in ["LAST NAME", "SURNAME"]):
                if i + 1 < len(lines):
                    data['last_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}
            
            if any(k in txt for k in ["GIVEN NAME", "FIRST NAME"]):
                if i + 1 < len(lines):
                    data['first_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}

        # Fallback for names if specific labels weren't found
        if not data['last_name']['value']:
            candidates = [l for l in lines if len(l['text']) > 3 and not any(x in l['text'].upper() for x in ["PHILHEALTH", "REPUBLIC", "ID", "NUMBER"])]
            if len(candidates) >= 2:
                data['last_name'] = {"value": candidates[0]['text'].title(), "confidence": candidates[0]['confidence'] * 0.7}
                data['first_name'] = {"value": candidates[1]['text'].title(), "confidence": candidates[1]['confidence'] * 0.7}

        return data
