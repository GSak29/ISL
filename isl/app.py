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

app = Flask(__name__)

# Load environment variables
# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Global variables
model = None
is_detection_running = False
detected_words = []
last_detection_time = 0
last_llm_update_time = 0
api_key_valid = False  # Track if API key is actually working

def validate_api_key():
    global api_key_valid
    if not API_KEY:
        api_key_valid = False
        return
    
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        # Minimal test payload
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            api_key_valid = True
            print("✅ API Key verified successfully.")
        else:
            api_key_valid = False
            print(f"❌ API Key validation failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ API Key validation error: {e}")
        api_key_valid = False

# Run validation on startup
threading.Thread(target=validate_api_key, daemon=True).start()
DETECTION_INTERVAL = 1.0  # Update detection every 1 second
LLM_UPDATE_INTERVAL = 5.0  # Update LLM every 5 seconds
frame_queue = queue.Queue(maxsize=2)
camera_thread_obj = None
llm_thread = None
cached_translation = ""
show_boxes = True
last_detected_word = None
last_detected_time = 0
WORD_COOLDOWN = 2.0  # Minimum time between same word detections
WORD_HISTORY = []  # Store last few detected words
MAX_HISTORY = 3  # Maximum number of words to keep in history

def load_model():
    base_path = os.path.dirname(os.path.abspath(__file__))
    model_file = "general_best.pt"  # Always use general model
    model_path = os.path.join(base_path, "weights", model_file)
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}")
    return YOLO(model_path)

def fallback_translation(words):
    if not words:
        return '"No words detected."'
    
    # Basic grammar rules for simple sentences
    if len(words) == 1:
        return f'"{words[0]}."'
    elif len(words) == 2:
        return f'"{words[0]} {words[1]}."'
    else:
        # Very basic sentence formation
        return f'"{" ".join(words)}."'


# Validates key on startup, but we also want to catch runtime 401s
api_key_invalid_forever = False

def generate_sentence_groq(words):
    global api_key_invalid_forever
    
    if not API_KEY:
        # print("Warning: API Key missing, using fallback") # Reduce noise
        return fallback_translation(words)

    if api_key_invalid_forever:
        return fallback_translation(words)

    joined = " ".join(words)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that converts grammatically incorrect or incomplete phrases into full meaningful English sentences. Always enclose your translation in double quotes."},
            {"role": "user", "content": f"Convert this: '{joined}' into a proper English sentence and enclose your answer in double quotes."}
        ],
        "temperature": 0.7
    }
    
    # Implement retry mechanism with fallback
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                if not (content.startswith('"') and content.endswith('"')):
                    content = f'"{content}"'
                return content

            # ❌ PERMANENT ERROR — DO NOT RETRY
            if response.status_code == 400:
                print("Permanent API error (400). Not retrying.")
                return fallback_translation(words)
                
            if response.status_code == 401:
                print("Invalid API Key (401). Disabling AI features for this session.")
                api_key_invalid_forever = True
                return fallback_translation(words)

            # 🔁 TEMPORARY ERRORS — RETRY
            if response.status_code in (429, 503, 500, 502):
                print(f"Temporary API error ({response.status_code}). Retrying...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

            # ❌ Any other unexpected error → fallback
            print(f"Unhandled API error: {response.status_code}")
            return fallback_translation(words)

        except requests.exceptions.Timeout:
            print("Timeout. Retrying...")
            time.sleep(retry_delay)
            retry_delay *= 2

        except Exception as e:
            print("Unexpected exception:", e)
            return fallback_translation(words)
            
    return fallback_translation(words)

def update_translation_async(words):
    global cached_translation
    try:
        cached_translation = generate_sentence_groq(words)
    except Exception as e:
        print(f"Async translation error: {e}")




def camera_thread():
    global is_detection_running
    camera = None
    
    # List of backends to try on Windows
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    
    try:
        # Try different indices and backends
        for i in range(2): # Try index 0 and 1
            if camera is not None and camera.isOpened():
                break
                
            for backend in backends:
                try:
                    print(f"Attempting camera index {i} with backend {backend}")
                    temp_cam = cv2.VideoCapture(i, backend)
                    
                    if temp_cam.isOpened():
                        # Read a test frame
                        ret, frame = temp_cam.read()
                        if ret and frame is not None:
                            camera = temp_cam
                            print(f"Success! Camera initialized at index {i} with backend {backend}")
                            break
                        else:
                            temp_cam.release()
                except Exception as e:
                    print(f"Failed to init camera {i} backend {backend}: {e}")
                    
        if camera is None or not camera.isOpened():
            print("CRITICAL ERROR: Could not open any camera source.")
            is_detection_running = False
            return
            
        # Set settings
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        camera.set(cv2.CAP_PROP_FPS, 30)

        error_count = 0
        while is_detection_running:
            success, frame = camera.read()
            if not success or frame is None:
                error_count += 1
                if error_count > 10:
                    print("Too many consecutive frame errors. Stopping.")
                    break
                time.sleep(0.1)
                continue
            
            error_count = 0 # Reset error count on success
            
            try:
                if frame_queue.full():
                    frame_queue.get_nowait()
                frame_queue.put(frame.copy())
            except queue.Full:
                pass
            except Exception as e:
                print(f"Error in frame queue: {e}")
            
            time.sleep(0.01)
    
    except Exception as e:
        print(f"Camera thread fatal error: {e}")
    finally:
        if camera is not None:
            camera.release()
        print("Camera released")
        is_detection_running = False

def generate_frames():
    global model, is_detection_running, detected_words, last_detection_time, last_llm_update_time, cached_translation, last_detected_word, last_detected_time, WORD_HISTORY, llm_thread
    
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
                        # Only start new thread if previous one finished
                        if llm_thread is None or not llm_thread.is_alive():
                            llm_thread = threading.Thread(target=update_translation_async, args=(list(detected_words),))
                            llm_thread.daemon = True
                            llm_thread.start()
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
    return render_template('index.html')

@app.route('/detection')
def detection():
    # Load background image - REMOVED in favor of CSS styling
    # bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Extra", "bg.jpg")
    # bg_image = None
    # if os.path.exists(bg_path):
    #     with open(bg_path, "rb") as img_file:
    #         bg_image = base64.b64encode(img_file.read()).decode()
    
    return render_template('detection.html')

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
        show_boxes = data.get('show_boxes', True)
        
        # Load model
        try:
            model = load_model()
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

@app.route('/animation')
def animation():
    return render_template('animation.html')

@app.route('/api/process_speech', methods=['POST'])
def process_speech():
    """Process speech text using Groq to improve grammar and extract meaningful words"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    # Use the existing generate_sentence_groq function logic but adapted
    # If API_KEY is present, we try to get a better version of the text
    meaningful_text = text
    
    if API_KEY:
        try:
            # We want to convert spoken "chunks" into a proper sentence or keywords
            # Re-using generate_sentence_groq logic essentially
            processed = generate_sentence_groq(text.split())
            # Remove quotes added by the helper
            meaningful_text = processed.strip('"')
        except Exception as e:
            print(f"Error processing speech with AI: {e}")
            # Fallback to original text
            meaningful_text = text
            
    return jsonify({
        'original': text,
        'processed': meaningful_text
    })

@app.route('/api/grok-key', methods=['GET'])
def get_grok_key():
    """API endpoint to check AI service status"""
    if API_KEY:
        if api_key_valid:
            return jsonify({'status': 'online', 'message': 'AI Service Operational'})
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid API Key. Please check your .env file.',
                'code': 'INVALID_KEY'
            }), 401
    else:
        return jsonify({
            'status': 'error',
            'message': 'API Key missing from .env file',
            'code': 'MISSING_KEY'
        }), 404

if __name__ == '__main__':
    app.run(debug=True)