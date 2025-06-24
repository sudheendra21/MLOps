
# Flask Depth Anything V2 API

REST API for depth estimation using Depth Anything V2. Analyzes depth at specific object locations and provides depth visualizations.

## Quick Setup

```bash
# clone this repository

# Install dependencies
pip install -r requirements.txt

# Create checkpoints directory and download model if checkpoint folder doesnt exist
mkdir checkpoints
cd checkpoints
```

Download the pre-trained model:

| Model | Size | Download |
|:-|:-:|:-:|
| Depth-Anything-V2-Small | 24.8M | [Download](https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth?download=true) |

Save as `checkpoints/depth_anything_v2_vits.pth`

```bash
# Run the API
python app.py
```

API runs on `http://localhost:5050`

## Endpoints

- `POST /predict_depth` - Depth prediction with object midpoints
- `GET /model-info` - Model information  
- `GET /health` - Health check

## Usage

**Request Format:**
- `image`: Image file (required)
- `midpoints`: JSON array of object locations (required)
- `detection_count`: Number of detected objects
- `image_info`: Additional image metadata
- `include_images`: `true`/`false` - Include depth visualizations

**Response:**
```json
{
  "success": true,
  "depth_stats": {
    "min_depth": 0.12,
    "max_depth": 45.67,
    "mean_depth": 12.34,
    "std_depth": 8.91
  },
  "depth_at_objects": [
    {
      "x": 150, "y": 200,
      "depth_value": 15.23,
      "class_name": "person",
      "confidence": 0.892
    }
  ],
  "images": {
    "depth_visualization": "data:image/jpeg;base64,..."
  }
}
```

## Configuration

Edit `DEPTH_CONFIG` in `app.py`:
- `encoder`: Model size (`vits`, `vitb`, `vitl`, `vitg`)
- `input_size`: Input image size (default: 518)
- `checkpoint_path`: Path to model weights
- `device`: `cuda`/`mps`/`cpu` (auto-detected)

## Supported Formats

PNG, JPG, JPEG, GIF, BMP, WebP (max 16MB)

