from flask import Flask, Response, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import threading
import os
import cv2

class Drone:
    # Class Attrs:
    # There probably will be only one instance.



    def __init__(self, secret_key='temp_key', video_dir=None):
        # Instance Attrs:
        
        if secret_key=='temp_key':
            print("WARNING: Secret key not configured.")

        if video_dir:
            print("WARNING: Video directory not specified, reverting to \'./videos\'")

        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secret_key
        self.video_dir = "./videos" if video_dir is None else video_dir

    def generate_token(self, username):
        """
        Create a timed token to authorise Requests to video stream.
        """
        s = URLSafeTimedSerializer(self.app.config(['SECRET_KEY']))
        return s.dumps({'username':username})
    
    def verify_token(self, token):
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
        
    def read_frames():
        pass

    def generate_frames():
        pass

    