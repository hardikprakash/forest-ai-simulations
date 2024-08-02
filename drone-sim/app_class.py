from flask import Flask, Response, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import threading
import os
import cv2
import time

class Drone:

    def __init__(self, secret_key='temp_key', video_dir=None):
        # Instance Attrs:
        
        if secret_key=='temp_key':
            print("WARNING: Secret key not configured.")

        if video_dir:
            print("WARNING: Video directory not specified, reverting to \'./videos\'")

        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secret_key
        self.video_dir = "./videos" if video_dir is None else video_dir
        dir_files = os.listdir(self.video_dir)
        
        # Update together, incoherent update implies API call
        self.locations = [i.split(".")[0] for i in dir_files if i.endswith(".mp4")]
        self.current_location = 0
        self.navigation_requested, self.navigate_to = False, None
        self.frame_buffer, self.frame_lock = None, threading.Lock()

    def generate_token(self, username):
        """
        Create a timed token to authorise Requests to video stream.
        """
        s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
        return s.dumps({'username':username})
    
    def verify_token(self, token):
        """
        Verify incoming token.
        """
        s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
        
        try:
            data = s.loads(token)
            print(data)
            return data['username']
            
        except SignatureExpired:
            print("ERROR: Signature Expired.")
            return None
        
        except BadSignature:
            print("ERROR: Bad signature.")
            return None
    
    def navigate_path(self):
        """
        Navigate to specified location, or navigate to next, if not specified.
        """
        if self.navigate_to is None:
            if self.current_location < len(self.locations)-1:
                self.current_location+=1
                return
            else:
                self.current_location = 0
                return
            
        elif isinstance(self.navigate_to, int) and self.navigate_to < len(self.locations):
            self.current_location = self.navigate_to
            return
        
        else:
            print("WARNING: Unexpected navigation behavior, resetting to location 0.")
            self.current_location = 0
            return

    def read_frames(self):
        """
        Read frames from video files on fs, and keep video capture running between "navigations."
        """
        while True:

            video_path = self.video_dir + self.locations[self.current_location]
            video = cv2.VideoCapture(video_path)

            while True:

                # External Navigation Request
                if self.navigation_requested:
                    self.navigate_path()
                    self.navigation_requested = False
                    self.navigate_to = None
                    break

                success, frame = video.read()

                # Navigate because EOF
                if not success:
                    self.navigate_path()
                    break

                with self.frame_lock:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    self.frame_buffer = buffer.tobytes()
                
                time.sleep(1/24)
        

    def generate_frames(self):
        """
        Generate frames which can be sent as responses.
        """
        while True:
            with self.frame_lock:
                if self.frame_buffer is not None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.frame_buffer + b'\r\n')
    
    def init_routes(self):

        @self.app.route('/login', methods=['POST'])
        def login():
            username = request.json.get('username')
            password = request.json.get('password')
            
            if (username == 'testUser' and password == 'testPass'):
                token = self.generate_token(username=username)
                return jsonify({'token': token})
            
            return jsonify({'message: Invalid credentials.'}), 401

        @self.app.route('/video')
        def video():
            
            token = request.args.get('token')
            
            if not token:
                return jsonify({'message': 'Missing token.'}), 401

            username = self.verify_token(token)
            if not username:
                return jsonify({'message': 'Invalid or expired token.'}), 401
    
            return Response(self.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    drone = Drone()
    drone.init_routes()

    # Start the video reading in a separate thread
    video_thread = threading.Thread(target=drone.read_frames)
    video_thread.daemon = True
    video_thread.start()

    drone.app.run(host='0.0.0.0', port=5001)
