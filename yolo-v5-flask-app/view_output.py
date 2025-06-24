import requests
import json
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

def draw_bounding_boxes(image_path, detections, output_filename="detected_objects.jpg"):
    """Draw bounding boxes on the image"""
    
    # Load original image
    image = Image.open(image_path)
    annotated_image = image.copy()
    draw = ImageDraw.Draw(annotated_image)
    
    # Define colors for different classes
    colors = [
        "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
        "#FFA500", "#800080", "#FFC0CB", "#A52A2A", "#808080", "#000080",
        "#008000", "#FF69B4", "#DC143C", "#4B0082", "#FF4500", "#2E8B57"
    ]
    
    print(f"Drawing {len(detections)} bounding boxes...")
    
    for i, detection in enumerate(detections):
        bbox = detection['bbox_xyxy']  # [x1, y1, x2, y2]
        class_name = detection['class_name']
        confidence = detection['confidence']
        
        # Choose color
        color = colors[i % len(colors)]
        
        # Draw bounding box
        draw.rectangle(bbox, outline=color, width=3)
        
        # Prepare label
        label = f"{class_name}: {confidence:.2f}"
        
        # Try to use a better font
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
            except:
                font = ImageFont.load_default()
        
        # Get text size
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position label
        label_x = bbox[0]
        label_y = bbox[1] - text_height - 5
        if label_y < 0:
            label_y = bbox[1] + 5
        
        # Draw label background
        draw.rectangle(
            [label_x, label_y, label_x + text_width + 10, label_y + text_height + 5],
            fill=color
        )
        
        # Draw label text
        draw.text((label_x + 5, label_y + 2), label, fill="white", font=font)
        
        print(f"    {i+1}. {class_name} at [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
    
    # Save annotated image
    annotated_image.save(output_filename)
    print(f" Annotated image saved as: {output_filename}")
    
    return annotated_image

def create_side_by_side_comparison(original_path, detections, output_filename="comparison.jpg"):
    """Create side-by-side comparison of original and annotated images"""
    
    # Load original
    original = Image.open(original_path)
    
    # Create annotated version
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    
    colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]
    
    for i, det in enumerate(detections):
        bbox = det['bbox_xyxy']
        color = colors[i % len(colors)]
        
        # Draw box and label
        draw.rectangle(bbox, outline=color, width=2)
        label = f"{det['class_name']}: {det['confidence']:.2f}"
        draw.text((bbox[0], bbox[1] - 15), label, fill=color)
    
    # Create side-by-side image
    total_width = original.width * 2 + 20  # Add some spacing
    comparison = Image.new('RGB', (total_width, original.height + 40), 'white')
    
    # Paste images
    comparison.paste(original, (10, 30))
    comparison.paste(annotated, (original.width + 10, 30))
    
    # Add titles
    draw_comp = ImageDraw.Draw(comparison)
    try:
        title_font = ImageFont.truetype("arial.ttf", 20)
    except:
        title_font = ImageFont.load_default()
    
    draw_comp.text((10, 5), "Original", fill="black", font=title_font)
    draw_comp.text((original.width + 10, 5), f"Detected ({len(detections)} objects)", fill="black", font=title_font)
    
    comparison.save(output_filename)
    print(f" Comparison image saved as: {output_filename}")
    
    return comparison

def quick_test():
    """Quick test of the simplified API with bounding box visualization"""
    
    base_url = "http://127.0.0.1:5000"
    image_path = "data/images/bus.jpg"
    
    print(" Quick API Test with Bounding Box Visualization")
    print("="*55)
    
    # Step 1: Check if API is running
    try:
        health = requests.get(f"{base_url}/health")
        if health.status_code == 200:
            health_data = health.json()
            print("API is running")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Device: {health_data.get('device')}")
            print(f"   Classes: {health_data.get('model_classes')}")
        else:
            print("API not responding")
            return
    except Exception as e:
        print(f"Cannot connect to API: {e}")
        print("Make sure the API is running: python app_simplified.py --weights yolov5s.pt")
        return
    
    # Step 2: Check if image exists
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        print("Make sure the image file exists")
        return
    
    print(f" Using image: {image_path}")
    
    # Step 3: Convert image to DocArray JSON
    print(" Converting image to DocArray...")
    
    try:
        response = requests.post(
            f"{base_url}/path_to_docarray",
            json={"image_path": image_path}
        )
        
        if response.status_code == 200:
            result = response.json()
            docarray_json = result['docarray_json']
            print(f"DocArray created with {len(docarray_json)} documents")
        else:
            print(f"Failed to create DocArray: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f" Error creating DocArray: {e}")
        return
    
    # Step 4: Run detection
    print(" Running YOLO detection...")
    
    try:
        response = requests.post(
            f"{base_url}/detect",
            json={"docarray_json": docarray_json}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Detection successful!")
            print(f"Image size: {result['image_info']['width']}x{result['image_info']['height']}")
            print(f"Objects found: {result['num_detections']}")
            print(f"Device: {result['model_info']['device']}")
            print(f"Confidence threshold: {result['model_info']['confidence_threshold']}")
            
            detections = result['detections']
            
            # Show detection summary
            if detections:
                print(f"\nDetected Objects:")
                for i, det in enumerate(detections, 1):
                    bbox = det['bbox_xyxy']
                    print(f"   {i}. {det['class_name']}: {det['confidence']:.3f}")
                    print(f"      Box: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
                
                # Step 5: Draw bounding boxes
                print(f"\nDrawing bounding boxes...")
                
                # Draw individual annotated image
                annotated_img = draw_bounding_boxes(image_path, detections, "bus_detected.jpg")
                
                # Create side-by-side comparison
                comparison_img = create_side_by_side_comparison(image_path, detections, "bus_comparison.jpg")
                
                print(f"\n Images created:")
                print(f"     bus_detected.jpg   - Image with bounding boxes")
                print(f"     bus_comparison.jpg - Side-by-side comparison")
                
                # Save detection results to JSON
                with open("detection_results.json", "w") as f:
                    json.dump(result, f, indent=2)
                print(f"    detection_results.json - Full API response")
                
                # Try to open the images automatically
                import os
                import platform
                
                try:
                    if platform.system() == "Windows":
                        os.startfile("bus_comparison.jpg")
                    elif platform.system() == "Darwin":  # macOS
                        os.system("open bus_comparison.jpg")
                    else:  # Linux
                        os.system("xdg-open bus_comparison.jpg")
                    print(f"  Opening comparison image...")
                except:
                    print(f" Manually open 'bus_comparison.jpg' to see the results!")
                
            else:
                print(f"\n No objects detected in the image")
                
        else:
            print(f" Detection failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f" Detection error: {e}")
    
    print(f"\n" + "="*55)
    print(" TEST COMPLETE")
    print("="*55)

if __name__ == "__main__":
    quick_test()