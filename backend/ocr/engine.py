import os
import re
import json
import cv2
import numpy as np
import traceback

# CRITICAL: Set environment variables BEFORE importing paddle
# These prevent SegFaults and initialization hangs on ARM64/RPi
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("!!! PaddleOCR library not found. Ensure 'pip install paddleocr paddlepaddle' was successful. !!!")

class OCRProcessor:
    def __init__(self):
        print("--- Initializing PaddleOCR (RPi ARM64 Optimized) ---")
        self.ocr = None
        
        try:
            # We use the most minimal configuration possible to avoid "Unknown argument" errors
            # which can occur in specific versions of PaddleOCR or under Python 3.13.
            # PaddleOCR defaults to CPU when GPU is not available.
            # Environment variables above (OMP_NUM_THREADS) handle the performance/stability.
            self.ocr = PaddleOCR(
                lang='en',
                use_angle_cls=True
            )
            print("--- PaddleOCR Engine Ready ---")
        except Exception as e:
            print("!!! OCR INITIALIZATION FAILED !!!")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            # Print full traceback to terminal to help debug
            traceback.print_exc()
            self.ocr = None

    def preprocess_image(self, img_path):
        """Prepare image for OCR using OpenCV"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None
            
        h, w = img.shape[:2]
        max_dim = 1024 
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img, gray

    def process_image(self, img_path):
        if self.ocr is None:
            raise RuntimeError(
                "OCR Engine is not initialized. "
                "Please check the backend terminal for initialization errors."
            )
            
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found at {img_path}")

        try:
            # Inference call
            result = self.ocr.ocr(img_path, cls=True)
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
                "ocr_engine": "paddleocr-rpi-stable",
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
