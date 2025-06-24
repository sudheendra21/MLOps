from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import io
import json
import base64
import numpy as np
from PIL import Image
import cv2
import torch
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
import tempfile
import traceback

# Import Depth Anything V2 components
try:
    from depth_anything_v2.dpt import DepthAnythingV2
except ImportError as e:
    print(f"Warning: Depth Anything V2 imports failed: {e}")
    print("Make sure depth_anything_v2 is properly installed")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Depth Anything V2 Configuration
DEPTH_CONFIG = {
    'encoder': 'vits',  # Change to 'vitb', 'vitl', or 'vitg' as needed
    'input_size': 518,
    'checkpoint_path': 'checkpoints/depth_anything_v2_vits.pth',  # Update path as needed
    'device': 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu',
    'grayscale': False,
    'pred_only': False
}

# Global model variable
depth_model = None
device = None

def load_depth_model():
    """Load Depth Anything V2 model once on startup"""
    global depth_model, device
    
    try:
        device = DEPTH_CONFIG['device']
        
        # Model configurations
        model_configs = {
            'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
            'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
            'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
            'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
        }
        
        # Initialize model
        encoder = DEPTH_CONFIG['encoder']
        depth_model = DepthAnythingV2(**model_configs[encoder])
        
        # Load checkpoint
        checkpoint_path = DEPTH_CONFIG['checkpoint_path']
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
            
        depth_model.load_state_dict(torch.load(checkpoint_path, map_location='cpu'))
        depth_model = depth_model.to(device).eval()
        
        print(f"Depth Anything V2 model loaded successfully on {device}")
        print(f"Encoder: {encoder}")
        print(f"Checkpoint: {checkpoint_path}")
        return True
        
    except Exception as e:
        print(f"Error loading Depth Anything V2 model: {e}")
        traceback.print_exc()
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_file):
    """Preprocess image for depth estimation"""
    try:
        # Read image from file object
        image = Image.open(image_file).convert('RGB')
        img_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV (Depth Anything expects BGR)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_bgr, img_array
        
    except Exception as e:
        raise Exception(f"Error preprocessing image: {e}")

def estimate_depth(img_bgr):
    """Run depth estimation on image"""
    try:
        with torch.no_grad():
            depth = depth_model.infer_image(img_bgr, DEPTH_CONFIG['input_size'])
        
        # Normalize depth to 0-255 range
        depth_normalized = (depth - depth.min()) / (depth.max() - depth.min()) * 255.0
        depth_uint8 = depth_normalized.astype(np.uint8)
        
        return depth, depth_uint8
        
    except Exception as e:
        raise Exception(f"Error during depth estimation: {e}")

def create_depth_visualization(raw_image, depth_uint8):
    """Create depth visualization with colormap"""
    try:
        cmap = matplotlib.colormaps.get_cmap('Spectral_r')
        
        if DEPTH_CONFIG['grayscale']:
            depth_colored = np.repeat(depth_uint8[..., np.newaxis], 3, axis=-1)
        else:
            depth_colored = (cmap(depth_uint8)[:, :, :3] * 255)[:, :, ::-1].astype(np.uint8)
        
        if DEPTH_CONFIG['pred_only']:
            result = depth_colored
        else:
            # Create side-by-side comparison
            split_region = np.ones((raw_image.shape[0], 50, 3), dtype=np.uint8) * 255
            result = cv2.hconcat([raw_image, split_region, depth_colored])
        
        return result, depth_colored
        
    except Exception as e:
        raise Exception(f"Error creating depth visualization: {e}")

def extract_depth_at_midpoints(depth_map, midpoints):
    """Extract depth values at specified midpoints"""
    try:
        depth_values = []
        h, w = depth_map.shape
        
        for midpoint in midpoints:
            x, y = midpoint['x'], midpoint['y']
            
            # Ensure coordinates are within image bounds
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            
            # Extract depth value at midpoint
            depth_value = float(depth_map[y, x])
            
            depth_info = {
                'x': x,
                'y': y,
                'depth_value': depth_value,
                'class_name': midpoint.get('class_name', 'unknown'),
                'confidence': midpoint.get('confidence', 0.0),
                'bbox': midpoint.get('bbox', {})
            }
            
            depth_values.append(depth_info)
            
        return depth_values
        
    except Exception as e:
        raise Exception(f"Error extracting depth at midpoints: {e}")

def encode_image_to_base64(img_array):
    """Convert image array to base64 string"""
    try:
        # Convert BGR to RGB if needed
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = img_array
            
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

@app.route('/predict_depth', methods=['POST'])
def predict_depth():
    """Main endpoint for depth prediction with object midpoints"""
    try:
        # Check if model is loaded
        if depth_model is None:
            return jsonify({'error': 'Depth model not loaded'}), 500
        
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
        
        # Get midpoints data
        midpoints_json = request.form.get('midpoints', '[]')
        try:
            midpoints = json.loads(midpoints_json)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid midpoints JSON data'}), 400
        
        # Get additional data
        detection_count = int(request.form.get('detection_count', 0))
        image_info_json = request.form.get('image_info', '{}')
        try:
            image_info = json.loads(image_info_json)
        except json.JSONDecodeError:
            image_info = {}
        
        # Reset file pointer to beginning
        file.seek(0)
        
        # Preprocess image
        img_bgr, img_rgb = preprocess_image(file)
        
        # Estimate depth
        depth_map, depth_uint8 = estimate_depth(img_bgr)
        
        # Create depth visualization
        depth_viz, depth_colored = create_depth_visualization(img_bgr, depth_uint8)
        
        # Extract depth values at midpoints
        depth_at_midpoints = extract_depth_at_midpoints(depth_map, midpoints)
        
        # Calculate statistics
        depth_stats = {
            'min_depth': float(depth_map.min()),
            'max_depth': float(depth_map.max()),
            'mean_depth': float(depth_map.mean()),
            'std_depth': float(depth_map.std())
        }
        
        # Prepare response
        response_data = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'model_info': {
                'encoder': DEPTH_CONFIG['encoder'],
                'input_size': DEPTH_CONFIG['input_size'],
                'device': str(device)
            },
            'image_info': {
                'filename': file.filename,
                'original_size': img_bgr.shape[:2],  # (height, width)
                **image_info
            },
            'detection_info': {
                'detection_count': detection_count,
                'midpoints_processed': len(midpoints)
            },
            'depth_stats': depth_stats,
            'depth_at_objects': depth_at_midpoints
        }
        
        # Include images if requested
        include_images = request.form.get('include_images', 'true').lower() == 'true'
        if include_images:
            response_data['images'] = {
                'depth_visualization': encode_image_to_base64(depth_viz),
                'depth_colored': encode_image_to_base64(depth_colored)
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error in depth prediction: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Depth prediction failed: {str(e)}'}), 500

@app.route('/model-info', methods=['GET'])
def model_info():
    """Get information about the loaded depth model"""
    if depth_model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    return jsonify({
        'model_loaded': True,
        'device': str(device),
        'config': DEPTH_CONFIG,
        'checkpoint_exists': os.path.exists(DEPTH_CONFIG['checkpoint_path'])
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask Depth Anything V2 API is running',
        'model_loaded': depth_model is not None,
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE // (1024 * 1024)
    }), 200


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'}), 413

if __name__ == '__main__':
    print(f"Device: {DEPTH_CONFIG['device']}")
    print(f"Encoder: {DEPTH_CONFIG['encoder']}")
    
    # Load Depth Anything V2 model
    print("Loading Depth Anything V2 model...")
    if load_depth_model():
        print("Depth Anything V2 Model loaded successfully")
    else:
        print("✗ Failed to load model - API will not work properly")
    
    app.run(debug=True, host='0.0.0.0', port=5050)