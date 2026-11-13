import cv2
import json

MARKER_WIDTH = 5.0

# Load calibration
with open("calibration.json", "r") as f:
    calibration = json.load(f)

focal_length = calibration["focal_length"]

# ArUco setup
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

while True:

    ret, frame = camera.read()

    if not ret:
        break

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:

        aruco.drawDetectedMarkers(frame, corners, ids)

        for marker_corners in corners:

            points = marker_corners[0]

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

            distance = (
                focal_length *
                MARKER_WIDTH /
                pixel_width
            )

            cv2.putText(
                frame,
                f"Distance: {distance:.1f} cm",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

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

    cv2.imshow("Smart Side Mirror", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()