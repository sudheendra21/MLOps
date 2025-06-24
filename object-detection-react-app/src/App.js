import React, { useState } from 'react';
import './App.css';

// Parse query string parameters
// Example URL: http://localhost:3000/?yoloapp=http://127.0.0.1:5000&depthapi=http://localhost:5050
var qs = (function(a) {
	if (a === "") return {};
	var b = {};
	for (var i = 0; i < a.length; ++i)
	{
		var p=a[i].split('=', 2);
		if (p.length === 1)
			b[p[0]] = "";
		else
			b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
	}
	return b;
})(window.location.search.substr(1).split('&'));

console.log("qs object:", qs);
console.log("qs['yoloapi']:", qs['yoloapi']);
console.log("qs['depthapi']:", qs['depthapi']);
console.log("Type of qs['yoloapp']:", typeof qs['yoloapp']);

const App = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [detectionResults, setDetectionResults] = useState(null);
  const [depthResults, setDepthResults] = useState(null);
  const [annotatedImageUrl, setAnnotatedImageUrl] = useState(null);
  const [depthVisualizationUrl, setDepthVisualizationUrl] = useState(null);

  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedImage(file);
      
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target.result);
      };
      reader.readAsDataURL(file);
      setStatus('');
      setDetectionResults(null);
      setDepthResults(null);
      setAnnotatedImageUrl(null);
      setDepthVisualizationUrl(null);
    } else {
      setStatus('Please select a valid image file');
    }
  };

  const calculateMidpoints = (detections) => {
    return detections.map(detection => {
      const { bbox, class_name, confidence } = detection;
      const midX = Math.round((bbox.x1 + bbox.x2) / 2);
      const midY = Math.round((bbox.y1 + bbox.y2) / 2);
      
      return {
        x: midX,
        y: midY,
        class_name: class_name,
        confidence: confidence,
        bbox: bbox
      };
    });
  };

  const processImage = async () => {
    if (!selectedImage) {
      setStatus('Please select an image first');
      return;
    }

    setLoading(true);
    setStatus('Running object detection...');
    setDetectionResults(null);
    setDepthResults(null);

    try {
      // Step 1: Run YOLOv5 detection
      const formData = new FormData();
      formData.append('image', selectedImage);
      formData.append('include_image', 'true');

      // const detectionResponse = await fetch('http://127.0.0.1:5000/detect', {
      //   method: 'POST',
      //   body: formData,
      // });

      const baseUrl = qs['yoloapi'];
      const detectionResponse = await fetch(`${baseUrl}/detect`, {
        method: 'POST',
        body: formData,
      });

      if (!detectionResponse.ok) {
        throw new Error(`Detection failed! status: ${detectionResponse.status}`);
      }

      const detectionData = await detectionResponse.json();
      // console.log('Detection results:', detectionData);
      
      setDetectionResults(detectionData);
      
      if (detectionData.annotated_image) {
        setAnnotatedImageUrl(detectionData.annotated_image);
      }

      if (detectionData.detections && detectionData.detections.length > 0) {
        setStatus('Processing depth prediction...');
        
        const midpoints = calculateMidpoints(detectionData.detections);
        // console.log('Calculated midpoints:', midpoints);

        // Step 2: Send to depth prediction API
        const depthFormData = new FormData();
        depthFormData.append('image', selectedImage);
        depthFormData.append('midpoints', JSON.stringify(midpoints));
        depthFormData.append('detection_count', detectionData.detection_count.toString());
        depthFormData.append('image_info', JSON.stringify(detectionData.image_info));
        depthFormData.append('include_images', 'true');

        // const depthResponse = await fetch('http://localhost:5050/predict_depth', {
        //   method: 'POST',
        //   body: depthFormData,
        // });

        const baseUrl = qs['depthapi'];
        const depthResponse = await fetch(`${baseUrl}/predict_depth`, {
          method: 'POST',
          body: depthFormData,
        });

        if (!depthResponse.ok) {
          throw new Error(`Depth prediction failed! status: ${depthResponse.status}`);
        }

        const depthData = await depthResponse.json();
        // console.log('Depth prediction results:', depthData);
        
        setDepthResults(depthData);
        
        if (depthData.images && depthData.images.depth_visualization) {
          setDepthVisualizationUrl(depthData.images.depth_visualization);
        }
        
        setStatus('success');
      } else {
        setStatus('No objects detected in the image');
      }

    } catch (error) {
      console.error('Error processing image:', error);
      setStatus(`Processing failed: ${error.message}. Make sure both API servers are running.`);
    } finally {
      setLoading(false);
    }
  };



  const renderDetectionResults = () => {
    if (!detectionResults) return null;

    return (
      <div className="results-section">
        <div className="results-header">
          <h3 className="results-title">Detection Results</h3>
          <span className="detection-count">{detectionResults.detection_count} objects found</span>
        </div>
        
        <div className="detections-list">
          {detectionResults.detections.map((detection, index) => {
            const midX = Math.round((detection.bbox.x1 + detection.bbox.x2) / 2);
            const midY = Math.round((detection.bbox.y1 + detection.bbox.y2) / 2);
            
            return (
              <div key={index} className="detection-item">
                <div className="detection-info">
                  <span className="class-name">{detection.class_name}</span>
                  <span className="confidence">{(detection.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="detection-details">
                  <div className="bbox-info">
                    <span>BBox: ({detection.bbox.x1}, {detection.bbox.y1}) → ({detection.bbox.x2}, {detection.bbox.y2})</span>
                  </div>
                  <div className="midpoint-info">
                    <span>Midpoint: ({midX}, {midY})</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderDepthMetrics = () => {
    if (!depthResults || !depthResults.depth_at_objects) return null;

    return (
      <div className="results-section">
        <div className="results-header">
          <h3 className="results-title">Depth Metrics</h3>
          <span className="detection-count">{depthResults.depth_at_objects.length} objects analyzed</span>
        </div>
        
        <div className="depth-metrics">
          {depthResults.depth_at_objects.map((depthInfo, index) => (
            <div key={index} className="depth-metric-item">
              <div className="metric-header">
                <span className="object-name">{depthInfo.class_name}</span>
                <span className="object-confidence">{(depthInfo.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="metric-details">
                <div className="metric-row">
                  <span className="metric-label">Position:</span>
                  <span className="metric-value">({depthInfo.x}, {depthInfo.y})</span>
                </div>
                <div className="metric-row">
                  <span className="metric-label">Depth Value:</span>
                  <span className="metric-value depth-value">{depthInfo.depth_value.toFixed(2)} units</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderDepthStats = () => {
    if (!depthResults || !depthResults.depth_stats) return null;

    const stats = depthResults.depth_stats;
    return (
      <div className="results-section">
        <div className="results-header">
          <h3 className="results-title">Overall Depth Statistics</h3>
        </div>
        
        <div className="depth-stats">
          <div className="stat-item">
            <span className="stat-label">Min Depth:</span>
            <span className="stat-value">{stats.min_depth.toFixed(2)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Max Depth:</span>
            <span className="stat-value">{stats.max_depth.toFixed(2)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Mean Depth:</span>
            <span className="stat-value">{stats.mean_depth.toFixed(2)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Std Deviation:</span>
            <span className="stat-value">{stats.std_depth.toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      <div className="container">
        {/* Header */}
        <div className="header">
          <h1 className="title">AI Object Detection & Depth Prediction</h1>
          <p className="subtitle">Upload images for YOLOv5 detection and depth analysis</p>
        </div>

        {/* Upload Section */}
        <div className="upload-card">
          <h2 className="card-title">Upload Image</h2>
          
          <div className="upload-section">
            <label className="upload-label">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="upload-input"
              />
              <div className="upload-area">
                <div className="upload-icon">
                  <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="upload-text">Drop your image here or click to browse</p>
                <p className="upload-info">PNG, JPG, GIF up to 16MB</p>
              </div>
            </label>
          </div>

          {selectedImage && (
            <div className="file-info">
              <div className="file-indicator"></div>
              <div>
                <p className="file-name">{selectedImage.name}</p>
                <p className="file-size">{Math.round(selectedImage.size / 1024)} KB</p>
              </div>
            </div>
          )}

          <button
            onClick={processImage}
            disabled={!selectedImage || loading}
            className={`upload-button ${loading ? 'loading' : ''} ${!selectedImage ? 'disabled' : ''}`}
          >
            {loading ? (
              <div className="button-content">
                <div className="spinner"></div>
                {status.includes('detection') ? 'Detecting Objects...' : 'Processing Depth...'}
              </div>
            ) : (
              <div className="button-content">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Analyze Image
              </div>
            )}
          </button>

          {/* Status Messages */}
          {status && status !== 'success' && !loading && (
            <div className="status-error">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <p>{status}</p>
            </div>
          )}

          {status === 'success' && (
            <div className="status-success">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>Analysis completed successfully!</p>
            </div>
          )}

          {loading && (
            <div className="status-processing">
              <div className="spinner"></div>
              <p>{status}</p>
            </div>
          )}
        </div>

        {/* Large Image Display Section */}
        <div className="image-display-section">
          <div className="image-grid">
            {/* Original Image */}
            {imagePreview && (
              <div className="large-image-container">
                <h3 className="image-title">Original Image</h3>
                <div className="large-image-frame">
                  <img
                    src={imagePreview}
                    alt="Original"
                    className="large-image"
                  />
                </div>
              </div>
            )}

            {/* Detected Objects Image */}
            {annotatedImageUrl && (
              <div className="large-image-container">
                <h3 className="image-title">Detected Objects</h3>
                <div className="large-image-frame detected-frame">
                  <img
                    src={annotatedImageUrl}
                    alt="With detections"
                    className="large-image"
                  />
                </div>
              </div>
            )}

            {/* Depth Visualization */}
            {depthVisualizationUrl && (
              <div className="large-image-container">
                <h3 className="image-title">Depth Visualization</h3>
                <div className="large-image-frame depth-frame">
                  <img
                    src={depthVisualizationUrl}
                    alt="Depth visualization"
                    className="large-image"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Results Section */}
        {(detectionResults || depthResults) && (
          <div className="results-container">
            {renderDetectionResults()}
            {renderDepthMetrics()}
            {renderDepthStats()}
          </div>
        )}

        {/* API Status */}
        <div className="api-status">
          <div className="api-info">
            <div className="api-indicator"></div>
            <span>Detection API: POST {qs['yoloapi'] }/detect</span>
          </div>
          <div className="api-info">
            <div className="api-indicator depth-indicator"></div>
            <span>Depth API: POST {qs['depthapi'] }/predict_depth</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;