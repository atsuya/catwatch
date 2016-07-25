import collections
import io
import numpy as np
import picamera
import picamera.array
import random
import signal
import sys
import threading
import time

RESOLUTION_WIDTH = 1280
RESOLUTION_HEIGHT = 720
FRAME_RATE = 24
BUFFER_SECONDS = 20
#SPLITTER_RECORDING = 2
#SPLITTER_MOTION_DETECTION = 1
MOTION_DETECTION_QUEUE = FRAME_RATE
MOTION_DETECTION_THRESHOLD = 2

class MotionDetector(picamera.array.PiMotionAnalysis):
    def initialize(self):
        self.motion_detections = collections.deque(maxlen=MOTION_DETECTION_QUEUE)
        self.clear()

    def is_detected(self):
        return self.motion_detections.count(1) >= MOTION_DETECTION_THRESHOLD

    def clear(self):
        for i in range(0, self.motion_detections.maxlen):
            self.motion_detections.append(0)

    def analyze(self, a):
        #print('Analyze')
        #print("motion detected: {0}, {1}".format(self.is_detected(), self.motion_detections))

        a = np.sqrt(
            np.square(a['x'].astype(np.float)) +
            np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        # If there're more than 10 vectors with a magnitude greater
        # than 60, then say we've detected motion
        motion_detected = 0
        if (a > 60).sum() > 10:
            motion_detected = 1

        self.motion_detections.append(motion_detected)

def sigint_handler(signal, frame):
    global exiting

    print("SIGINT detected")
    exiting = True

#
# main
#
exiting = False

camera = picamera.PiCamera(framerate=FRAME_RATE)
camera.resolution = (RESOLUTION_WIDTH, RESOLUTION_HEIGHT)
camera.exposure_mode = 'night'

stream = picamera.PiCameraCircularIO(camera, seconds=BUFFER_SECONDS)

motion_detector = MotionDetector(camera)
motion_detector.initialize()

camera.start_recording(stream, format='h264', motion_output=motion_detector)

signal.signal(signal.SIGINT, sigint_handler)

try:
    while exiting is not True:
        motion_detector.clear()
        print("start motion detection")
        camera.wait_recording(1)
        print("end motion detection")
        if motion_detector.is_detected():
            print("motion detected! recording next {0} seconds.".format(BUFFER_SECONDS / 2))
            camera.wait_recording(timeout=BUFFER_SECONDS / 2)
            filename = "video-{0}-{1}.h264".format(time.strftime("%Y-%m-%d-%H-%M-%S"), int(round(time.time() * 1000)))
            stream.copy_to(filename)
            print("saved: {0}".format(filename))
except BaseException as exception:
    print("Exception main".format(exception))
finally:
    camera.stop_recording()
