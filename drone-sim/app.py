from flask import Flask, request, Response, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import threading
import os
import cv2
import time
from enum import Enum
import itertools
import sys


users = {
    "testUser": "testPass"
}

# Global Variables
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'temp_key')
video_dir = os.environ.get('VIDEO_PATH', './videos/')

# Auto detect all .mp4 files in ./videos directory
# Might need to create locks if API reads available locations.
locations = os.listdir(video_dir)
locations = [i for i in locations if (i.endswith(".mp4"))]
n_locations = len(locations)
if n_locations == 0:
    print("No video files, exiting.")
    sys.exit()

# >>Itertools is compromising random location access.
# location_loop = itertools.cycle(locations)
# current_location = next(location_loop)

move_ahead = False

# Auth Token Management
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

def navigate_path(to_location=None):
    """
    Will simply move to next location if called without arguments.
    Will try to move to a valid location if specified. Else, it logs an error to console and exits without changing location.
    """
    global current_location, locations, n_locations
    
    # Move to next location
    # Set video position to zero

    if to_location is not None:
        if not (to_location<n_locations):
            print("Invalid location specified, moving ")
        current_location = to_location
        return

    if current_location < n_locations-1:
        current_location+=1
        return
    
    else:
        current_location=0
        return


frame_buffer, frame_lock = None, threading.Lock()

def read_frames(video_path):
    global frame_buffer
    
    # Create video path:
    video_path = video_dir + locations[current_location]
    video = cv2.VideoCapture(video_path)

    # >>Handle random location jumps.
    # global move_ahead

    # if move_ahead is True:
    #     navigate_path


    while True:
        success, frame = video.read()

        # Video has ended
        # Move to next location
        if not success:
            # Video has ended
            # Move to next location
    

            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            navigate_path()
            continue

        with frame_lock:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_buffer = buffer.tobytes()

        time.sleep(1/23.98)

def generate_frames():
    global frame_buffer

    while True:
        with frame_lock:
            if frame_buffer is not None:
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_buffer + b'\r\n')


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if username in users and users[username] == password:
        token = generate_token(username)
        return jsonify({'token': token})
    
    return jsonify({'message': 'Invalid Credentials.'}), 401

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

    video_thread = threading.Thread(target=read_frames, args=(video_path,))
    video_thread.daemon = True
    video_thread.start()

    app.run(host='0.0.0.0', port=5001)