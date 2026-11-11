import cv2

aruco = cv2.aruco

dictionary = aruco.getPredefinedDictionary(
    aruco.DICT_4X4_50
)

marker = aruco.generateImageMarker(
    dictionary,
    0,
    600
)

cv2.imwrite("marker.png", marker)

print("Marker generated successfully!")