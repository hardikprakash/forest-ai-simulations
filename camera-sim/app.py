import cv2
import os
import requests
import threading
import time
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoStreamer:
    def __init__(self, video_path, backend_url, login_url, username, password):
        self.video_path = video_path
        self.backend_url = backend_url
        self.login_url = login_url
        self.username = username
        self.password = password
        self.token = None
        self.frame_buffer = None
        self.frame_lock = threading.Lock()
        self.capture = cv2.VideoCapture(video_path)
        
        if not self.capture.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            sys.exit()

        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 23.98  # Default to 23.98 if FPS is not available
        self.get_token()

    def get_token(self):
        """Request a new token from the backend"""
        try:
            response = requests.post(self.login_url, data={"username": self.username, "password": self.password})
            if response.status_code == 200:
                self.token = response.json().get("token")
                logger.info("Token successfully retrieved.")
            else:
                logger.error(f"Failed to retrieve token: {response.status_code} - {response.text}")
                sys.exit()
        except Exception as e:
            logger.error(f"Exception occurred while retrieving token: {e}")
            sys.exit()

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

    def upload_frames(self):
        while True:
            with self.frame_lock:
                if self.frame_buffer is not None:
                    headers = {'Authorization': f'Bearer {self.token}'}
                    response = requests.post(self.backend_url, files={"file": self.frame_buffer}, headers=headers)

                    if response.status_code == 401:  # Token expired or invalid
                        logger.warning("Token expired, requesting a new token.")
                        self.get_token()
                        continue  # Retry with the new token
                    elif response.status_code != 200:
                        logger.error(f"Failed to upload frame: {response.status_code} - {response.text}")
                    else:
                        logger.info(f"Frame uploaded successfully: {response.status_code}")
            
            time.sleep(0.5)  # Send 2 frames per second (0.5 seconds interval)

# Config
video_path = './videos/video1.mp4'
backend_url = 'http://localhost:8000/upload'
login_url = 'http://localhost:8000/login'
username = 'testUser'
password = 'testPass'

if __name__ == '__main__':
    video_streamer = VideoStreamer(video_path, backend_url, login_url, username, password)
    
    # Thread: Read video.
    video_thread = threading.Thread(target=video_streamer.read_frames)
    video_thread.daemon = True
    video_thread.start()

    # Thread: Upload video.
    upload_thread = threading.Thread(target=video_streamer.upload_frames)
    upload_thread.daemon = True
    upload_thread.start()

    logger.info("Video streaming script running.")
    upload_thread.join()
