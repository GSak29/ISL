from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
from ultralytics import YOLO
import os
from dotenv import load_dotenv
import requests
import time
import threading
import queue
import base64
import torch

# PyTorch 2.6 switched torch.load default to weights_only=True which breaks
# older Ultralytics checkpoints that rely on model class pickling.
# We proactively allowlist Ultralytics' DetectionModel in the safe loader.
try:
    from ultralytics.nn.tasks import DetectionModel  # type: ignore
except Exception:  # pragma: no cover - best effort import
    DetectionModel = None  # type: ignore


def allowlist_ultralytics_for_torch_unpickler() -> None:
    """Allowlist Ultralytics DetectionModel for PyTorch's safe unpickler.

    On PyTorch >= 2.6, torch.load defaults to weights_only=True and uses a
    restricted unpickler that rejects unknown globals. Ultralytics models
    saved with older versions may reference `ultralytics.nn.tasks.DetectionModel`.
    Adding it to the safe list allows loading from trusted sources.
    """
    if DetectionModel is None:
        return

    add_safe_globals = getattr(torch.serialization, "add_safe_globals", None)
    if callable(add_safe_globals):
        try:
            add_safe_globals([DetectionModel])
        except Exception:
            # Best-effort; fall back to context manager during load if needed
            pass

app = Flask(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

# Global variables
model = None
is_detection_running = False
detected_words = []
last_detection_time = 0
last_llm_update_time = 0
DETECTION_INTERVAL = 1.0  # Update detection every 1 second
LLM_UPDATE_INTERVAL = 5.0  # Update LLM every 5 seconds
frame_queue = queue.Queue(maxsize=2)
camera_thread_obj = None
cached_translation = ""
show_boxes = True
last_detected_word = None
last_detected_time = 0
WORD_COOLDOWN = 2.0  # Minimum time between same word detections
WORD_HISTORY = []  # Store last few detected words
MAX_HISTORY = 3  # Maximum number of words to keep in history

def load_model(is_hospital_mode):
    model_path = "weights/hospital_best.pt" if is_hospital_mode else "weights/general_best.pt"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}")

    # Prepare PyTorch safe-loading allowlist
    allowlist_ultralytics_for_torch_unpickler()

    # First attempt: normal load (works on most setups)
    try:
        return YOLO(model_path)
    except Exception as initial_error:
        # Fallback: try loading within safe_globals context on newer PyTorch
        safe_globals_ctx = getattr(torch.serialization, "safe_globals", None)
        if callable(safe_globals_ctx) and DetectionModel is not None:
            try:
                with torch.serialization.safe_globals([DetectionModel]):
                    return YOLO(model_path)
            except Exception:
                pass
        # If all attempts fail, raise the original, more informative error
        raise initial_error

def generate_sentence_groq(words):
    joined = " ".join(words)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that converts grammatically incorrect or incomplete phrases into full meaningful English sentences."},
            {"role": "user", "content": f"Convert this: '{joined}'"}
        ],
        "temperature": 0.7
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return "Translation error."

def camera_thread():
    global is_detection_running
    camera = None
    try:
        # Try to open camera with different indices
        for i in range(3):  # Try first 3 camera indices
            try:
                print(f"Attempting to open camera at index {i}")
                camera = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Use DirectShow backend on Windows
                
                # Add a small delay after opening
                time.sleep(1)
                
                if camera.isOpened():
                    # Verify camera is working by reading a test frame
                    ret, test_frame = camera.read()
                    if ret and test_frame is not None:
                        print(f"Successfully opened and verified camera at index {i}")
                        # Set camera properties
                        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        camera.set(cv2.CAP_PROP_FPS, 30)
                        
                        # Verify camera properties
                        width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        fps = camera.get(cv2.CAP_PROP_FPS)
                        print(f"Camera properties - Width: {width}, Height: {height}, FPS: {fps}")
                        break
                    else:
                        print(f"Camera at index {i} opened but failed to read frame")
                        camera.release()
                        camera = None
                else:
                    print(f"Failed to open camera at index {i}")
                    if camera is not None:
                        camera.release()
                        camera = None
            except Exception as e:
                print(f"Error opening camera at index {i}: {e}")
                if camera is not None:
                    camera.release()
                    camera = None
                continue
        
        if camera is None or not camera.isOpened():
            print("Error: Could not open any camera")
            is_detection_running = False
            return
            
        print("Camera initialized successfully")
        
        while is_detection_running:
            try:
                success, frame = camera.read()
                if not success or frame is None:
                    print("Failed to grab frame")
                    # Try to recover camera
                    print("Attempting to recover camera connection...")
                    camera.release()
                    time.sleep(1)
                    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    if not camera.isOpened():
                        print("Failed to recover camera connection")
                        is_detection_running = False
                        break
                    continue
                
                try:
                    if frame_queue.full():
                        frame_queue.get_nowait()  # Remove old frame
                    frame_queue.put(frame.copy())
                except queue.Full:
                    continue
                except Exception as e:
                    print(f"Error in frame queue: {e}")
                    continue
                
                # Add a small sleep to prevent CPU overload
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error in camera loop: {e}")
                break
    
    except Exception as e:
        print(f"Camera thread error: {e}")
    finally:
        if camera is not None:
            camera.release()
        print("Camera released")
        is_detection_running = False

def generate_frames():
    global model, is_detection_running, detected_words, last_detection_time, last_llm_update_time, cached_translation, last_detected_word, last_detected_time, WORD_HISTORY
    
    while is_detection_running:
        try:
            frame = frame_queue.get(timeout=1.0)
            current_time = time.time()
            
            # Run detection at specified interval
            if current_time - last_detection_time >= DETECTION_INTERVAL:
                try:
                    results = model(frame)
                    
                    if results[0].boxes.cls.numel() > 0:
                        current_labels = [model.names[int(cls)] for cls in results[0].boxes.cls]
                        for label in current_labels:
                            # Check if it's a new word or enough time has passed since the last detection
                            if (label != last_detected_word or 
                                current_time - last_detected_time >= WORD_COOLDOWN):
                                # Check if the word is not in recent history
                                if label not in WORD_HISTORY:
                                    if label not in detected_words:
                                        detected_words.append(label)
                                    last_detected_word = label
                                    last_detected_time = current_time
                                    
                                    # Update word history
                                    WORD_HISTORY.append(label)
                                    if len(WORD_HISTORY) > MAX_HISTORY:
                                        WORD_HISTORY.pop(0)
                    
                    last_detection_time = current_time
                    
                    # Update LLM output at specified interval
                    if current_time - last_llm_update_time >= LLM_UPDATE_INTERVAL and detected_words:
                        cached_translation = generate_sentence_groq(detected_words)
                        last_llm_update_time = current_time
                    
                    # Draw bounding boxes if enabled
                    if show_boxes:
                        annotated_frame = results[0].plot()
                    else:
                        annotated_frame = frame
                except Exception as e:
                    print(f"Detection error: {e}")
                    annotated_frame = frame
            else:
                annotated_frame = frame

            # Convert frame to JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Frame generation error: {e}")
            continue

@app.route('/')
def index():
    # Load background image
    bg_path = "Extra/bg.jpg"
    bg_image = None
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as img_file:
            bg_image = base64.b64encode(img_file.read()).decode()
    
    return render_template('index.html', bg_image=bg_image)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    global model, is_detection_running, detected_words, camera_thread_obj, frame_queue, show_boxes, last_detected_word, last_detected_time, WORD_HISTORY
    
    try:
        # Check if detection is already running
        if is_detection_running:
            return jsonify({'status': 'error', 'message': 'Detection is already running'}), 400
            
        # Clear any existing frames
        while not frame_queue.empty():
            frame_queue.get_nowait()
            
        data = request.json
        is_hospital_mode = data.get('hospital_mode', False)
        show_boxes = data.get('show_boxes', True)
        
        # Load model
        try:
            model = load_model(is_hospital_mode)
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Failed to load model: {str(e)}'}), 500
        
        # Initialize detection state
        is_detection_running = True
        detected_words = []
        last_detected_word = None
        last_detected_time = 0
        WORD_HISTORY = []
        
        # Start camera thread
        camera_thread_obj = threading.Thread(target=camera_thread)
        camera_thread_obj.daemon = True
        camera_thread_obj.start()
        
        # Wait for camera initialization with timeout
        timeout = 5  # 5 seconds timeout
        start_time = time.time()
        while camera_thread_obj.is_alive() and time.time() - start_time < timeout:
            if not frame_queue.empty():
                # Camera is working if we have frames
                return jsonify({'status': 'success', 'message': 'Camera initialized successfully'})
            time.sleep(0.1)
            
        # Check if camera thread is still alive and producing frames
        if not camera_thread_obj.is_alive() or frame_queue.empty():
            is_detection_running = False
            return jsonify({'status': 'error', 'message': 'Camera initialization failed - no frames received'}), 500
            
        return jsonify({'status': 'success', 'message': 'Camera initialized successfully'})
    except Exception as e:
        print(f"Start detection error: {e}")
        is_detection_running = False
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global is_detection_running, camera_thread_obj, frame_queue, last_detected_word, last_detected_time, WORD_HISTORY
    
    try:
        is_detection_running = False
        
        while not frame_queue.empty():
            frame_queue.get_nowait()
            
        if camera_thread_obj and camera_thread_obj.is_alive():
            camera_thread_obj.join(timeout=2.0)
            
        last_detected_word = None
        last_detected_time = 0
        WORD_HISTORY = []
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Stop detection error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_detected_words', methods=['GET'])
def get_detected_words():
    global detected_words, cached_translation
    return jsonify({
        'words': detected_words,
        'full_sentence': ' '.join(detected_words),
        'translation': cached_translation
    })

@app.route('/clear_words', methods=['POST'])
def clear_words():
    global detected_words, cached_translation, last_detected_word, last_detected_time, WORD_HISTORY
    detected_words = []
    cached_translation = ""
    last_detected_word = None
    last_detected_time = 0
    WORD_HISTORY = []
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True) 