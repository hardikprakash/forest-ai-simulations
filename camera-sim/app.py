import cv2
import os
from flask import Flask, request, Response, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
import time
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoStreamer:
    def __init__(self, video_path):
        self.video_path = video_path
        self.frame_buffer = None
        self.frame_lock = threading.Lock()
        self.capture = cv2.VideoCapture(video_path)
        
        if not self.capture.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            sys.exit()

        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 23.98  # Default to 23.98 if FPS is not available

    def read_frames(self):
        while True:
            success, frame = self.capture.read()

            if not success or self.capture.get(cv2.CAP_PROP_POS_FRAMES) >= self.total_frames:
                logger.info(f"Video ended, resetting to start: {self.video_path}")
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to start of video
                continue

            with self.frame_lock:
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    logger.error("Failed to encode frame.")
                    continue
                self.frame_buffer = buffer.tobytes()

            time.sleep(1 / self.fps)  # Simulate frame rate

    def generate_frames(self):
        while True:
            with self.frame_lock:
                if self.frame_buffer is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.frame_buffer + b'\r\n')
            time.sleep(1 / self.fps)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback_key')
cur_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(cur_dir)
fallback_video_path = os.path.join(parent_dir, 'videos', 'vid.mp4')
video_path = os.environ.get('VIDEO_PATH', fallback_video_path)

if not app.config['SECRET_KEY']:
    logger.error("Secret key not configured. Exiting.")
    sys.exit()

if not video_path:
    logger.error("Video Path not configured. Exiting.")
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
        logger.warning("Token has expired.")
        return None
    except BadSignature:
        logger.warning("Invalid token signature.")
        return None

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if username in users and users[username] == password:
        token = generate_token(username)
        logger.info(f"User '{username}' logged in successfully.")
        return jsonify({'token': token})
    
    logger.warning(f"Invalid login attempt for user '{username}'.")
    return jsonify({'message': 'Invalid Credentials.'}), 401

@app.route('/video')
def video():
    token = request.args.get('token')
    if not token:
        logger.warning("Missing token in video stream request.")
        return jsonify({'message': 'Missing token.'}), 401
    
    username = verify_token(token)
    if not username:
        logger.warning("Invalid or expired token in video stream request.")
        return jsonify({'message': 'Invalid or expired token.'}), 401
    
    logger.info(f"User '{username}' is accessing the video stream.")
    return Response(video_streamer.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    video_streamer = VideoStreamer(video_path)
    
    # Start the video reading in a separate thread
    video_thread = threading.Thread(target=video_streamer.read_frames)
    video_thread.daemon = True
    video_thread.start()

    logger.info("Starting Flask server on port 5000.")
    app.run(host='0.0.0.0', port=5000)
