# Flask YOLOv5 Object Detection API

REST API for real-time object detection using YOLOv5.

## Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Clone YOLOv5
git clone https://github.com/pkrishna1801/yolo-v5-flask-app.git

# Run the API
python app.py
```

API runs on `http://127.0.0.1:5000`

## Endpoints

- `POST /detect` - Upload image for object detection
- `GET /health` - Health check
- `GET /model-info` - Model information

## Response Format

```json
{
  "success": true,
  "detections": [
    {
      "class_name": "person",
      "confidence": 0.892,
      "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 400}
    }
  ],
  "detection_count": 1
}
```

## Configuration

Edit `YOLO_CONFIG` in `app.py`:
- `conf_thres`: Confidence threshold (default: 0.25)
- `weights`: Model file (yolov5s.pt, yolov5m.pt, etc.)
- `device`: '' for auto, 'cpu' for CPU only

## Supported Formats

PNG, JPG, JPEG, GIF, BMP, WebP (max 16MB)