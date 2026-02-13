
# MedicMission Offline Registration

An offline-first patient registration system optimized for Raspberry Pi 5.

## Features
- **Local OCR**: Powered by PaddleOCR (No cloud required).
- **FastAPI Backend**: Efficient Python service with SQLite.
- **Modern UI**: Clean, medical-grade React frontend.
- **RPI Optimized**: Uses CPU-based inference and OpenCV preprocessing.

## 1. Prerequisites (Raspberry Pi 5)
- **OS**: Raspberry Pi OS (64-bit recommended).
- **Camera**: USB Webcam or RPi Camera Module.
- **Python**: 3.9+
- **Node.js**: 18+

## 2. Installation (Offline Ready)

### Backend Setup
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y libgl1 libglib2.0-0 libsm6 libxrender1 libxext6

# Setup environment
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn paddleocr paddlepaddle opencv-python sqlalchemy pydantic pillow python-multipart
```

### Frontend Setup
```bash
cd frontend
npm install
npm run build
```

## 3. Running the App

### Start Backend
```bash
cd backend
source venv/bin/activate
python main.py
```

### Start Frontend
Serve the build folder or run in dev mode:
```bash
cd frontend
npm run dev
```

## 4. Performance Tips for Raspberry Pi 5
1. **CPU Inference**: PaddleOCR automatically uses CPU if no GPU is found.
2. **Resolution**: The app captures at 1280x720. Higher resolutions significantly slow down OCR.
3. **Lighting**: OCR accuracy is 90% dependent on lighting. Avoid glares on ID cards.
4. **Boot Up**: PaddleOCR takes ~10-20 seconds to load the model into memory on the first run.

## 5. Troubleshooting
- **Camera Access**: Ensure the user is in the `video` group: `sudo usermod -a -G video $USER`.
- **CORS**: If accessing via network, update `allow_origins` in `main.py`.
- **Memory**: RPi 5 with 8GB is ideal; 4GB works but avoid opening many browser tabs.
- **Browser**: Use Chromium on RPi for best hardware acceleration support.
