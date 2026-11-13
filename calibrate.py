import cv2
import json

MARKER_WIDTH = 5.0

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

known_distance = 15.40

print("Place the toy car exactly 50 cm away.")
print("Press C to calibrate.")
print("Press Q to exit.")

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

        marker_corners = corners[0][0]

        marker_width_pixels = (
            sum([
                ((marker_corners[i][0] -
                  marker_corners[(i+1) % 4][0]) ** 2 +
                 (marker_corners[i][1] -
                  marker_corners[(i+1) % 4][1]) ** 2) ** 0.5
                for i in range(4)
            ]) / 4
        )

        cv2.putText(
            frame,
            "MARKER DETECTED - Press C",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        if cv2.waitKey(1) & 0xFF == ord('c'):

            focal_length = (
                marker_width_pixels *
                known_distance /
                MARKER_WIDTH
            )

            with open("calibration.json", "w") as f:

                json.dump(
                    {"focal_length": float(focal_length)},
                    f
                )

            print("Calibration successful!")
            print("Focal length:", focal_length)

            break

    cv2.imshow("Camera Calibration", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()