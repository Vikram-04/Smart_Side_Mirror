import cv2
import json
import time
import threading

from collections import deque
from flask import Flask, render_template, jsonify, Response

# ==========================================
# CONFIGURATION
# ==========================================

MARKER_WIDTH = 5.0

MIN_SAFE_DISTANCE = 100.0
MIN_SAFE_TTC = 3.0

CAMERA_INDEX = 0

# ==========================================
# FLASK
# ==========================================

app = Flask(__name__)

# ==========================================
# LOAD CALIBRATION
# ==========================================

with open("calibration.json", "r") as f:
    calibration = json.load(f)

focal_length = calibration["focal_length"]

# ==========================================
# ARUCO SETUP
# ==========================================

aruco = cv2.aruco

dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)

parameters = aruco.DetectorParameters()

detector = aruco.ArucoDetector(
    dictionary,
    parameters
)

# ==========================================
# SHARED DATA
# ==========================================

lock = threading.Lock()

dashboard_data = {
    "distance": None,
    "closing_speed": 0,
    "ttc": None,
    "status": "NO VEHICLE",
    "detected": False
}

latest_frame = None

distance_history = deque(maxlen=5)

previous_distance = None
previous_time = None

# ==========================================
# CAMERA PROCESSING
# ==========================================

def camera_worker():

    global latest_frame
    global previous_distance
    global previous_time

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("ERROR: Camera could not be opened.")
        return

    print("Camera started successfully.")

    while True:

        ret, frame = camera.read()

        if not ret:
            continue

        current_time = time.time()

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        corners, ids, rejected = detector.detectMarkers(gray)

        detected = False

        distance = None
        closing_speed = 0
        ttc = None

        status = "NO VEHICLE"

        if ids is not None:

            matching_indices = [
                i for i, marker_id in enumerate(ids.flatten())
                if marker_id == 0
            ]

            if matching_indices:

                index = matching_indices[0]

                points = corners[index][0]

                aruco.drawDetectedMarkers(
                    frame,
                    [corners[index]],
                    ids[index:index+1]
                )

                widths = []

                for i in range(4):

                    p1 = points[i]
                    p2 = points[(i+1) % 4]

                    width = (
                        (p1[0]-p2[0])**2 +
                        (p1[1]-p2[1])**2
                    )**0.5

                    widths.append(width)

                pixel_width = sum(widths) / 4

                if pixel_width > 0:

                    pixel_width = float(pixel_width)

                    raw_distance = float(
                        focal_length *
                        MARKER_WIDTH /
                        pixel_width
                    )

                    distance_history.append(raw_distance)

                    distance = sum(distance_history) / len(
                        distance_history
                    )

                    detected = True

                    # Calculate closing speed

                    if previous_distance is not None:

                        dt = current_time - previous_time

                        if dt > 0:

                            closing_speed = (
                                previous_distance - distance
                            ) / dt

                    # Calculate TTC

                    if closing_speed > 1:

                        ttc = distance / closing_speed

                    # Safety decision

                    if distance < MIN_SAFE_DISTANCE:

                        status = "UNSAFE"

                    elif ttc is not None and ttc < MIN_SAFE_TTC:

                        status = "UNSAFE"

                    else:

                        status = "SAFE"

                    previous_distance = distance
                    previous_time = current_time

                    # Draw distance on camera feed

                    cv2.putText(
                        frame,
                        f"Distance: {distance:.1f} cm",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2
                    )

        if not detected:

            previous_distance = None
            previous_time = None

            distance_history.clear()

        # Update shared dashboard information

        with lock:

            dashboard_data.update({
                "distance": float(round(float(distance), 1))
                    if distance is not None else None,

                "closing_speed": float(round(float(closing_speed), 1)),

                "ttc": float(round(float(ttc), 2))
                    if ttc is not None else None,

                "status": str(status),

                "detected": bool(detected)
            })

        # Encode camera frame for browser

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if success:

            with lock:
                latest_frame = buffer.tobytes()

    camera.release()


# ==========================================
# FRONTEND ROUTES
# ==========================================

@app.route("/")
def dashboard():

    return render_template("index.html")


# ==========================================
# API: DASHBOARD DATA
# ==========================================

@app.route("/api/status")
def get_status():

    with lock:

        data = dashboard_data.copy()

    return jsonify(data)


# ==========================================
# API: LIVE CAMERA FEED
# ==========================================

def generate_frames():

    while True:

        with lock:

            frame = latest_frame

        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )


@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    camera_thread = threading.Thread(
        target=camera_worker,
        daemon=True
    )

    camera_thread.start()

    print("Dashboard available at http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )