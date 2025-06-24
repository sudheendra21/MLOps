from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import io
import numpy as np
from PIL import Image
import torch
import cv2
from pathlib import Path
import tempfile
import base64


try:
    from models.common import DetectMultiBackend
    from utils.general import non_max_suppression, scale_boxes, xyxy2xywh
    from utils.torch_utils import select_device
    from utils.augmentations import letterbox
    from ultralytics.utils.plotting import Annotator, colors
except ImportError as e:
    print(f"Warning: YOLOv5 imports failed: {e}")
    print("Make sure YOLOv5 is properly installed and in your Python path")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# YOLOv5 Configuration
YOLO_CONFIG = {
    'weights': 'yolov5s.pt',  # Path to your model weights
    'device': '',  # '' for auto-detect, 'cpu' for CPU only, '0' for GPU 0
    'imgsz': 640,  # Image size for inference
    'conf_thres': 0.25,  # Confidence threshold
    'iou_thres': 0.45,  # IoU threshold for NMS
    'max_det': 1000,  # Maximum detections per image
    'classes': None,  # Filter by class (None for all classes)
    'agnostic_nms': False,  # Class-agnostic NMS
    'augment': False,  # Augmented inference
    'half': False,  # Use FP16 half-precision inference
}

# Global model variable (loaded once on startup)
model = None
device = None
names = None

def load_yolo_model():
    """Load YOLOv5 model once on startup"""
    global model, device, names
    
    try:
        device = select_device(YOLO_CONFIG['device'])
        model = DetectMultiBackend(
            YOLO_CONFIG['weights'], 
            device=device, 
            dnn=False, 
            fp16=YOLO_CONFIG['half']
        )
        names = model.names
        
        # Warmup
        imgsz = YOLO_CONFIG['imgsz']
        model.warmup(imgsz=(1, 3, imgsz, imgsz))
        
        print(f"YOLOv5 model loaded successfully on {device}")
        print(f"Model classes: {names}")
        return True
        
    except Exception as e:
        print(f"Error loading YOLOv5 model: {e}")
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_file):
    """Preprocess image for YOLOv5 inference"""
    try:
        # Read image from file object
        image = Image.open(image_file).convert('RGB')
        img_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Letterbox resize
        img_resized = letterbox(img_bgr, YOLO_CONFIG['imgsz'], stride=32, auto=True)[0]
        
        # Convert BGR to RGB, transpose and normalize
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_tensor = img_rgb.transpose((2, 0, 1))  # HWC to CHW
        img_tensor = np.ascontiguousarray(img_tensor)
        img_tensor = torch.from_numpy(img_tensor).to(device)
        img_tensor = img_tensor.float() / 255.0  # Normalize to 0-1
        
        if len(img_tensor.shape) == 3:
            img_tensor = img_tensor[None]  # Add batch dimension
            
        return img_tensor, img_bgr, img_array
        
    except Exception as e:
        raise Exception(f"Error preprocessing image: {e}")

def run_inference(img_tensor):
    """Run YOLOv5 inference on preprocessed image"""
    try:
        with torch.no_grad():
            pred = model(img_tensor, augment=YOLO_CONFIG['augment'])
            
        # Apply NMS
        pred = non_max_suppression(
            pred,
            YOLO_CONFIG['conf_thres'],
            YOLO_CONFIG['iou_thres'],
            YOLO_CONFIG['classes'],
            YOLO_CONFIG['agnostic_nms'],
            max_det=YOLO_CONFIG['max_det']
        )
        
        return pred
        
    except Exception as e:
        raise Exception(f"Error during inference: {e}")

def process_detections(pred, img_bgr, img_tensor):
    """Process detection results and return formatted data"""
    detections = []
    annotated_image = None
    
    try:
        det = pred[0]  # Get first (and only) image predictions
        
        if len(det):
            # Scale boxes from img_size to original image size
            det[:, :4] = scale_boxes(img_tensor.shape[2:], det[:, :4], img_bgr.shape).round()
            
            # Create annotator for drawing boxes
            annotator = Annotator(img_bgr, line_width=3, example=str(names))
            
            # Process each detection
            for *xyxy, conf, cls in det:
                class_id = int(cls)
                class_name = names[class_id]
                confidence = float(conf)
                
                # Convert coordinates to list
                bbox = [int(x) for x in xyxy]
                
                # Add detection to results
                detections.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': round(confidence, 3),
                    'bbox': {
                        'x1': bbox[0], 'y1': bbox[1],
                        'x2': bbox[2], 'y2': bbox[3]
                    }
                })
                
                # Draw bounding box on image
                label = f'{class_name} {confidence:.2f}'
                annotator.box_label(xyxy, label, color=colors(class_id, True))
            
            # Get annotated image
            annotated_image = annotator.result()
        else:
            annotated_image = img_bgr
            
        return detections, annotated_image
        
    except Exception as e:
        raise Exception(f"Error processing detections: {e}")

def encode_image_to_base64(img_array):
    """Convert image array to base64 string"""
    try:
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        img_pil.save(buffer, format='JPEG', quality=90)
        img_bytes = buffer.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
        
    except Exception as e:
        raise Exception(f"Error encoding image: {e}")

@app.route('/detect', methods=['POST'])
def detect_objects():
    """Main endpoint for object detection"""
    try:
        # Check if model is loaded
        if model is None:
            return jsonify({'error': 'YOLOv5 model not loaded'}), 500
        
        # Check if image file is in request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Reset file pointer to beginning
        file.seek(0)
        
        # Preprocess image
        img_tensor, img_bgr, original_img = preprocess_image(file)
        
        # Run inference
        predictions = run_inference(img_tensor)
        
        # Process detections
        detections, annotated_image = process_detections(predictions, img_bgr, img_tensor)
        print(f"Detections: {len(detections)} found")
        # print(detections)
        # Prepare response
        response_data = {
            'success': True,
            'detections': detections,
            'detection_count': len(detections),
            'image_info': {
                'filename': file.filename,
                'original_size': original_img.shape[:2],  # (height, width)
                'processed_size': img_bgr.shape[:2]
            }
        }
        
        # Include annotated image if requested
        include_image = request.form.get('include_image', 'false').lower() == 'true'
        if include_image:
            response_data['annotated_image'] = encode_image_to_base64(annotated_image)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error in object detection: {str(e)}")
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@app.route('/model-info', methods=['GET'])
def model_info():
    """Get information about the loaded model"""
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    return jsonify({
        'model_loaded': True,
        'device': str(device),
        'classes': names,
        'num_classes': len(names) if names else 0,
        'config': YOLO_CONFIG
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask YOLOv5 API is running',
        'model_loaded': model is not None,
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE // (1024 * 1024)
    }), 200

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'}), 413

if __name__ == '__main__':
    print("Starting Flask YOLOv5 API...")
    print(f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f"Max file size: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Load YOLOv5 model
    print("Loading YOLOv5 model...")
    if load_yolo_model():
        print("✓ Model loaded successfully")
    else:
        print("✗ Failed to load model - API will not work properly")
    
    
    app.run(debug=True, host='0.0.0.0', port=5000)