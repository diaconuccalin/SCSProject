from pyimagesearch.motion_detection import SingleMotionDetector
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template

import threading
import argparse
import imutils
import time
import cv2

# init output frame and a lock used in thread-safe exchanges of the output frames (useful when multiple clinets are viewing the stream)
outputFrame = None
lock = threading.Lock()

# init a flask object
app = Flask(__name__)

# init video stream
vs = VideoStream(src=0).start()

# imports and initializations for playing the alarm sound
from datetime import datetime, time
import math
import pyaudio

PyAudio = pyaudio.PyAudio

BITRATE = 16000
FREQUENCY = 800
LENGTH = 1

if FREQUENCY > BITRATE:
	BITRATE = FREQUENCY + 100
				
NUMBEROFFRAMES = int(BITRATE * LENGTH)
RESTFRAMES = NUMBEROFFRAMES % BITRATE
WAVEDATA = ''

for x in range(NUMBEROFFRAMES):
	WAVEDATA = WAVEDATA + chr(int(math.sin(x/((BITRATE/FREQUENCY)/math.pi))*127+128))

for x in range(RESTFRAMES):
	WAVEDATA = WAVEDATA + chr(128)


@app.route("/")
def index():
	return render_template("index.html")

# function to be used in a separate thread (such that it won't interfere with the motion detection) to play a tone
def playSound():
	p = PyAudio()
	stream = p.open(format = p.get_format_from_width(1), channels = 1, rate = BITRATE, output = True)

	stream.write(WAVEDATA)
	stream.stop_stream()
	stream.close()
	p.terminate()

def detect_motion(frameCount):
	global vs, outputFrame, lock

	md = SingleMotionDetector(accumWeight=0.1)
	total = 0

	prevTime = datetime.now()

	# loop over frames from he video stream
	while True:
		# read next frame, resize, grayscale, blur
		frame = vs.read()
		frame = imutils.resize(frame, width=400)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (7, 7), 0)

		# check if enough frames for bg model
		if total > frameCount:
			# detect motion
			motion = md.detect(gray)

			if motion is not None:
				# draw surrounding box
				(thresh, (minX, minY, maxX, maxY)) = motion
				cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)

				# play sound
				if((datetime.now() - prevTime).seconds > 1):
					prevTime = datetime.now()
					th = threading.Thread(target=playSound)
					th.daemon = True
					th.start()
		
		# update bg model
		md.update(gray)
		total += 1

		with lock:
			outputFrame = frame.copy()
		
def generate():
	global outputFrame, lock

	while True:
		with lock:
			if outputFrame is None:
				continue

			# encode frame as jpeg
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

			if not flag:
				continue

		# yield output frame in byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

# check if main thread
if __name__ == '__main__':
	# construct argument parser and parse command line arguments
	ap = argparse.ArgumentParser()
	ap.add_argument("-i", "--ip", type=str, required=True,
		help="ip address of the device")
	ap.add_argument("-o", "--port", type=int, required=True,
		help="ephemeral port number of the server (1024 to 65535)")
	ap.add_argument("-f", "--frame-count", type=int, default=32,
		help="# of frames used to construct the background model")
	args = vars(ap.parse_args())

	# start thread that will perform motion detection
	t = threading.Thread(target=detect_motion, args=(
		args["frame_count"],))
	t.daemon = True
	t.start()

	# start flask
	app.run(host=args["ip"], port=args["port"], debug=True,
		threaded=True, use_reloader=False)

# release video stream pointer
vs.stop()