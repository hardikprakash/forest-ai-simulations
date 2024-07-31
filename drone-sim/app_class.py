from flask import Flask, Response, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import threading
import os
import cv2

class Drone:
    # Class Attrs:
    # There probably will be only one instance.



    def __init__():
        # Instance Attrs:
        
        self.app = Flask(__name__)
        self.app.config['SECRET_K']
        
        pass

    def 

    