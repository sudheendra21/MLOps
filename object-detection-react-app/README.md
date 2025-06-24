# AI Object Detection & Depth Prediction App

React web app for YOLOv5 object detection with depth analysis.

## Setup

```bash
npm install
npm start
```

## Usage

1. Configure API endpoints via URL:
   ```
   http://localhost:3000/?yoloapi=http://127.0.0.1:5000&depthapi=http://localhost:5050
   ```

2. Upload image (PNG, JPG, GIF up to 16MB)
3. Click "Analyze Image"
4. View results: original → detected objects → depth visualization

## Required APIs

- **YOLOv5 API**: `POST /detect` - Object detection
- **Depth API**: `POST /predict_depth` - Depth prediction

## Features

- Drag & drop image upload
- Real-time processing status
- Side-by-side image comparison
- Detection metrics and depth statistics