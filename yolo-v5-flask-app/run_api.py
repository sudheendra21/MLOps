#!/usr/bin/env python3
"""
Run YOLOv5 Flask API with DetectMultiBackend
This script uses the same model loading logic as your detect.py
Supports the new workflow: Image Path → DocArray JSON → Model Processing → DocArray JSON
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='YOLOv5 Flask API Server with DocArray Workflow')
    
    # Model arguments (same as your detect.py)
    parser.add_argument('--weights', nargs='+', type=str, default='yolov5s.pt', 
                        help='model path or triton URL')
    parser.add_argument('--data', type=str, default='data/coco128.yaml', 
                        help='dataset.yaml path')
    parser.add_argument('--device', default='', 
                        help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--half', action='store_true', 
                        help='use FP16 half-precision inference')
    parser.add_argument('--dnn', action='store_true', 
                        help='use OpenCV DNN for ONNX inference')
    
    # API server arguments
    parser.add_argument('--host', default='0.0.0.0', 
                        help='host address')
    parser.add_argument('--port', type=int, default=5000, 
                        help='port number')
    parser.add_argument('--debug', action='store_true', 
                        help='run in debug mode')
    
    # Detection parameters (same as your detect.py)
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], 
                        help='inference size h,w')
    parser.add_argument('--conf-thres', type=float, default=0.25, 
                        help='confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, 
                        help='NMS IoU threshold')
    parser.add_argument('--max-det', type=int, default=1000, 
                        help='maximum detections per image')
    
    args = parser.parse_args()
    
    # Handle weights argument (can be single string or list)
    weights = args.weights[0] if isinstance(args.weights, list) else args.weights
    
    # Handle image size - ensure it's proper format
    if len(args.imgsz) == 1:
        imgsz = args.imgsz[0]  # Single integer
    elif len(args.imgsz) == 2:
        imgsz = tuple(args.imgsz)  # Tuple for rectangular
    else:
        imgsz = 640  # Default fallback
    
    print("="*60)
    print("YOLOv5 Flask API Server with DocArray Workflow")
    print("="*60)
    print(f"Model: {weights}")
    print(f"Device: {args.device if args.device else 'auto'}")
    print(f"Image size: {imgsz}")
    print(f"Confidence threshold: {args.conf_thres}")
    print(f"IoU threshold: {args.iou_thres}")
    print(f"Server: {args.host}:{args.port}")
    print(f"Debug mode: {args.debug}")
    print("="*60)
    
    # Import the Flask app components
    try:
        from app import app as flask_app, YOLOv5DetectorAPI
        import app as app_module
    except ImportError as e:
        print(f"Error importing Flask app: {e}")
        print("Make sure app.py is in the same directory")
        sys.exit(1)
    
    # Initialize detector with same parameters as your detect.py
    print("Initializing YOLOv5 detector...")
    
    try:
        detector = YOLOv5DetectorAPI(
            weights=weights,
            data=args.data,
            device=args.device,
            imgsz=imgsz,
            conf_thres=args.conf_thres,
            iou_thres=args.iou_thres,
            max_det=args.max_det,
            half=args.half,
            dnn=args.dnn
        )
        
        # Update the global detector in app module
        app_module.detector = detector
        
        print("Model loaded successfully")
        print(f"Device: {detector.device}")
        print(f"Classes: {list(detector.names.values())}")
        print(f"Model type: DetectMultiBackend")
        
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("\nTroubleshooting:")
        print("1. Check if the model file exists")
        print("2. Verify YOLOv5 dependencies are installed")
        print("3. Ensure CUDA is available if using GPU")
        sys.exit(1)
    
    
    # Run Flask app
    try:
        print(f"\n Starting Flask server on {args.host}:{args.port}")
        print("Press Ctrl+C to stop the server")
        print("="*60)
        
        flask_app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True,
            use_reloader=False  # Disable reloader to prevent double initialization
        )
        
    except KeyboardInterrupt:
        print("\n\n Server stopped by user")
        print("Goodbye!")
    except Exception as e:
        print(f"\n Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

