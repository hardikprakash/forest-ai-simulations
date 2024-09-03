import cv2
import os
from flask import Flask, request, Response, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Drone:
    def __init__(self, secret_key, video_path):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secret_key
        self.video_dir = video_path

        self.dir_files = [f for f in os.listdir(self.video_dir) if f.endswith(".mp4")]
        if not self.dir_files:
            logger.error("No video files found in the specified directory.")
            sys.exit("Exiting due to missing video files")

        # Locations mapped to filenames without extension
        self.locations = [os.path.splitext(f)[0] for f in self.dir_files]
        self.current_location = 0
        self.navigation_requested, self.navigate_to = False, None
        self.frame_buffer, self.frame_lock = None, threading.Lock()

    def generate_token(self, username):
        s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
        return s.dumps({'username': username})
    
    def verify_token(self, token):
        s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
            return data['username']
        except SignatureExpired:
            logger.warning("Token has expired.")
            return None
        except BadSignature:
            logger.warning("Invalid token signature.")
            return None

    def navigate_path(self):
        if self.navigate_to is None:
            self.current_location = (self.current_location + 1) % len(self.locations)
        elif isinstance(self.navigate_to, int) and 0 <= self.navigate_to < len(self.locations):
            self.current_location = self.navigate_to
            self.navigate_to, self.navigation_requested = None, False
        else:
            logger.warning("Unexpected navigation behavior, resetting to location 0.")
            self.current_location = 0

    def read_frames(self):
        while True:
            video_file = os.path.join(self.video_dir, self.locations[self.current_location] + '.mp4')
            vid_capture = cv2.VideoCapture(video_file)

            if not vid_capture.isOpened():
                logger.error(f"Failed to open video file: {video_file}")
                sys.exit("Exiting due to video file error")

            fps = vid_capture.get(cv2.CAP_PROP_FPS) or 23.98
            total_frames = int(vid_capture.get(cv2.CAP_PROP_FRAME_COUNT))

            while True:
                if self.navigation_requested:
                    self.navigate_path()
                    break

                success, frame = vid_capture.read()

                if not success or vid_capture.get(cv2.CAP_PROP_POS_FRAMES) >= total_frames:
                    self.navigate_path()
                    break

                with self.frame_lock:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if not ret:
                        logger.error("Failed to encode frame.")
                        continue
                    self.frame_buffer = buffer.tobytes()

                time.sleep(1 / fps)

    def generate_frames(self):
        while True:
            with self.frame_lock:
                if self.frame_buffer is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.frame_buffer + b'\r\n')
            time.sleep(0.1)  # Small delay to avoid busy-waiting

    def init_server(self):
        @self.app.route('/login', methods=['POST'])
        def login():
            username = request.json.get('username')
            password = request.json.get('password')
            
            if (username == 'testUser' and password == 'testPass'):
                token = self.generate_token(username=username)
                logger.info(f"User '{username}' logged in successfully.")
                return jsonify({'token': token})
            
            logger.warning(f"Invalid login attempt for user '{username}'.")
            return jsonify({'message': 'Invalid credentials.'}), 401
        
        @self.app.route('/video')
        def video():
            token = request.args.get('token')
            
            if not token:
                logger.warning("Missing token in video stream request.")
                return jsonify({'message': 'Missing token.'}), 401

            username = self.verify_token(token)
            if not username:
                logger.warning("Invalid or expired token in video stream request.")
                return jsonify({'message': 'Invalid or expired token.'}), 401
    
            logger.info(f"User '{username}' is accessing the video stream.")
            return Response(self.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback_key')
    video_path = os.environ.get('VIDEO_PATH', './videos')
    
    drone = Drone(secret_key=secret_key, video_path=video_path)

    video_thread = threading.Thread(target=drone.read_frames, daemon=True)
    video_thread.start()

    try:
        logger.info("Starting Flask server on port 5001.")
        drone.app.run(host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        logger.info("Exiting application.")
