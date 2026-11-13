import cv2
import json
import time
from collections import deque

# ---------------- CONFIGURATION ----------------

MARKER_WIDTH = 5.0

MIN_SAFE_DISTANCE = 100.0

MIN_SAFE_TTC = 3.0

# -----------------------------------------------

with open("calibration.json", "r") as f:
    calibration = json.load(f)

focal_length = calibration["focal_length"]

aruco = cv2.aruco

dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)

parameters = aruco.DetectorParameters()

detector = aruco.ArucoDetector(
    dictionary,
    parameters
)

camera = cv2.VideoCapture(0)

previous_distance = None
previous_time = None

# Smooth distance measurements
distance_history = deque(maxlen=5)

while True:

    ret, frame = camera.read()

    if not ret:
        break

    current_time = time.time()

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:

        # Find marker with ID 0
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

            raw_distance = (
                focal_length *
                MARKER_WIDTH /
                pixel_width
            )

            distance_history.append(raw_distance)

            distance = sum(distance_history) / len(
                distance_history
            )

            closing_speed = 0

            if previous_distance is not None:

                dt = current_time - previous_time

                if dt > 0:

                    closing_speed = (
                        previous_distance - distance
                    ) / dt

            ttc = float('inf')

            if closing_speed > 1:

                ttc = distance / closing_speed

            # Safety decision

            if distance < MIN_SAFE_DISTANCE:

                status = "UNSAFE TO CHANGE LANE"

            elif ttc < MIN_SAFE_TTC:

                status = "UNSAFE - VEHICLE APPROACHING"

            else:

                status = "SAFE TO CHANGE LANE"

            color = (
                (0, 0, 255)
                if status.startswith("UNSAFE")
                else (0, 255, 0)
            )

            # Display information

            cv2.putText(
                frame,
                f"Distance: {distance:.1f} cm",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Closing Speed: {closing_speed:.1f} cm/s",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            ttc_text = (
                f"TTC: {ttc:.1f} sec"
                if ttc != float('inf')
                else "TTC: No immediate collision"
            )

            cv2.putText(
                frame,
                ttc_text,
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                status,
                (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            previous_distance = distance
            previous_time = current_time

        else:

            cv2.putText(
                frame,
                "NO VEHICLE DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            previous_distance = None
            previous_time = None
            distance_history.clear()

    else:

        cv2.putText(
            frame,
            "NO VEHICLE DETECTED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        previous_distance = None
        previous_time = None
        distance_history.clear()

    cv2.imshow("SMART SIDE MIRROR - ROAD SAFETY SYSTEM", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()