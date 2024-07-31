import cv2
import os
from flask import Flask, request, Response, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
import time
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'temp_key')


video_path = os.environ.get('VIDEO_PATH', './videos/vid.mp4')

if app.config['SECRET_KEY'] == None:
    print("Secret key not configured. Exiting.")
    sys.exit()

if video_path == None:
    print("Video Path not configured. Exiting.")
    sys.exit()

users = {
    "testUser": "testPass"
}

def generate_token(username):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps({'username': username})

def verify_token(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
        return data['username']
    except SignatureExpired:
        return None
    except BadSignature:
        return None

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if username in users and users[username] == password:
        token = generate_token(username)
        return jsonify({'token': token})
    
    return jsonify({'message': 'Invalid Credentials.'}), 401

# Shared frame buffer and lock
frame_buffer = None
frame_lock = threading.Lock()

def read_frames(video_path):
    global frame_buffer
    video = cv2.VideoCapture(video_path)

    while True:
        success, frame = video.read()

        if not success:
            video.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to start of video
            continue

        with frame_lock:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_buffer = buffer.tobytes()

        time.sleep(1/23.98)  # Simulate frame rate

def generate_frames():
    global frame_buffer

    while True:
        with frame_lock:
            if frame_buffer is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_buffer + b'\r\n')
        time.sleep(1/23.98)  # Wait a bit before serving the next frame

@app.route('/video')
def video():
    token = request.args.get('token')
    if not token:
        return jsonify({'message': 'Missing token.'}), 401
    
    username = verify_token(token)
    if not username:
        return jsonify({'message': 'Invalid or expired token.'}), 401
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Start the video reading in a separate thread
    video_thread = threading.Thread(target=read_frames, args=(video_path,))
    video_thread.daemon = True
    video_thread.start()

    app.run(host='0.0.0.0', port=5000)
