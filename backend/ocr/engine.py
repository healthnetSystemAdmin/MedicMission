import os
import re
import json
import cv2
import numpy as np
from paddleocr import PaddleOCR

# Optimization for Raspberry Pi stability
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

class OCRProcessor:
    def __init__(self):
        print("--- Initializing PaddleOCR (RPi ARM64 Optimized) ---")
        try:
            # use_gpu=False: Explicitly use CPU
            # use_mp=False: CRITICAL - Disables multi-processing which causes SegFaults on RPi
            # lang='en': Standard alphanumeric for PhilHealth
            # use_angle_cls=True: Handle rotated IDs
            self.ocr = PaddleOCR(
                use_gpu=False,
                use_mp=False, 
                total_process_num=1,
                enable_mkldnn=False,
                use_angle_cls=True, 
                lang='en'
            )
            print("--- PaddleOCR Engine Ready ---")
        except Exception as e:
            print(f"!!! OCR Initialization Failed: {str(e)} !!!")
            # We don't re-raise here to allow the server to start even if OCR is offline
            self.ocr = None

    def preprocess_image(self, img_path):
        """Prepare image for OCR using OpenCV"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None
            
        # Resize for speed on RPi (Inference time scales with pixel count)
        h, w = img.shape[:2]
        max_dim = 1024 # Slightly smaller for better RPi performance
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # Grayscale can improve contrast for certain ID types
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img, gray

    def process_image(self, img_path):
        if self.ocr is None:
            raise RuntimeError("OCR Engine is not initialized")
            
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found at {img_path}")

        # Run OCR inference
        # result structure: [[ [ [points], (text, confidence) ], ... ]]
        try:
            result = self.ocr.ocr(img_path)
        except Exception as e:
            print(f"Inference Crash: {e}")
            raise RuntimeError(f"PaddleOCR Inference Failed: {str(e)}")
        
        lines = []
        if result and result[0]:
            for line in result[0]:
                lines.append({
                    "text": line[1][0],
                    "confidence": line[1][1]
                })

        # Heuristic Extraction
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
        """Regex and keyword based heuristic parser for PhilHealth cards"""
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
        
        # 1. PhilHealth ID Pattern (XX-XXXXXXXXX-X)
        id_pattern = r'(\d{2}-\d{9}-\d{1})'
        id_match = re.search(id_pattern, all_text)
        if id_match:
            data['philhealth_no'] = {"value": id_match.group(1), "confidence": 0.95}

        # 2. Sex Keywords
        if re.search(r'\b(MALE|M)\b', all_text, re.I):
            data['sex'] = {"value": "Male", "confidence": 0.9}
        elif re.search(r'\b(FEMALE|F)\b', all_text, re.I):
            data['sex'] = {"value": "Female", "confidence": 0.9}

        # 3. Simple Proximity Logic
        for i, line in enumerate(lines):
            txt = line['text'].upper()
            
            # Birth Date pattern
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})|(\d{2}-\d{2}-\d{4})', txt)
            if date_match and data['birth_date']['value'] == "":
                data['birth_date'] = {"value": date_match.group(0), "confidence": line['confidence']}

            # Search for labels
            if any(k in txt for k in ["LAST NAME", "SURNAME"]):
                if i + 1 < len(lines):
                    data['last_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}
            
            if any(k in txt for k in ["GIVEN NAME", "FIRST NAME"]):
                if i + 1 < len(lines):
                    data['first_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}

        # Fallback Logic
        if not data['last_name']['value']:
            candidates = [l for l in lines if len(l['text']) > 3 and not any(x in l['text'].upper() for x in ["PHILHEALTH", "REPUBLIC", "ID", "NUMBER"])]
            if len(candidates) >= 2:
                data['last_name'] = {"value": candidates[0]['text'].title(), "confidence": candidates[0]['confidence'] * 0.7}
                data['first_name'] = {"value": candidates[1]['text'].title(), "confidence": candidates[1]['confidence'] * 0.7}

        return data
