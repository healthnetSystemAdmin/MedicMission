import os
import re
import json
import cv2
import numpy as np
from paddleocr import PaddleOCR

class OCRProcessor:
    def __init__(self):
        # Initialize PaddleOCR
        # use_angle_cls=True helps with rotated images
        # lang='en' for standard alphanumeric cards
        # We set it here so it's globally active for this instance
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        print("--- PaddleOCR Engine Initialized (CPU Mode) ---")

    def preprocess_image(self, img_path):
        """Prepare image for OCR using OpenCV if needed"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None
            
        # 1. Resize for speed on RPi
        h, w = img.shape[:2]
        max_dim = 1280
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # 2. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img, gray

    def process_image(self, img_path):
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found at {img_path}")

        # Run OCR
        # We remove 'cls=True' here because 'use_angle_cls=True' was already set in __init__
        # This avoids the "unexpected keyword argument 'cls'" error in certain PaddleOCR versions.
        result = self.ocr.ocr(img_path)
        
        # Raw lines extraction
        # result structure: [[ [ [points], (text, confidence) ], ... ]]
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
                "ocr_engine": "paddleocr-rpi-opt",
                "notes": f"Detected {len(lines)} text blocks"
            }
        }

    def parse_fields(self, lines):
        """Regex and keyword based heuristic parser for PhilHealth cards"""
        
        # Defaults
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

        # 3. Simple Name Logic (Line based proximity)
        for i, line in enumerate(lines):
            txt = line['text'].upper()
            
            # Birth Date pattern (MM-DD-YYYY or Month DD, YYYY)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})|(\d{2}-\d{2}-\d{4})', txt)
            if date_match and data['birth_date']['value'] == "":
                data['birth_date'] = {"value": date_match.group(0), "confidence": line['confidence']}

            # Search for labels and take next line
            if "LAST NAME" in txt or "SURNAME" in txt:
                if i + 1 < len(lines):
                    data['last_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}
            
            if "GIVEN NAME" in txt or "FIRST NAME" in txt:
                if i + 1 < len(lines):
                    data['first_name'] = {"value": lines[i+1]['text'].title(), "confidence": lines[i+1]['confidence']}

        # Fallback for names if labels aren't found
        if not data['last_name']['value']:
            candidates = [l for l in lines if len(l['text']) > 3 and "PHILHEALTH" not in l['text'].upper() and "REPUBLIC" not in l['text'].upper()]
            if len(candidates) >= 2:
                data['last_name'] = {"value": candidates[0]['text'].title(), "confidence": candidates[0]['confidence'] * 0.7}
                data['first_name'] = {"value": candidates[1]['text'].title(), "confidence": candidates[1]['confidence'] * 0.7}

        return data
