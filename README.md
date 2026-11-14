# SMART SIDE MIRROR

## Project Details

**Domain:** Road Safety Engineering / Computer Vision\
**Repository:** https://github.com/Vikram-04/Smart_Side_Mirror

---

## 1. Summary

Smart Side Mirror is a camera-based prototype that estimates the
distance to a vehicle approaching from behind and evaluates whether the
situation should trigger a lane-change warning. A camera captures the
target. The software detects a known ArUco fiducial marker attached to
the test vehicle, estimates distance using camera calibration and the
marker's apparent pixel width, tracks distance over time, estimates
closing speed and time-to-collision (TTC), and displays the resulting
status on a Flask web dashboard.

The repository's stated objective is to calculate distance and TTC from
approaching vehicles and alert whether it is safe to switch lanes. The
current implementation is a controlled proof of concept: it detects a
specific marker (ID 0), not arbitrary unmarked vehicles.

**Safety scope:** This is an academic prototype, not a certified
Advanced Driver Assistance System (ADAS). A `SAFE` state means only that
the implemented thresholds are not currently violated under the
prototype's assumptions. It does not guarantee that a real lane change
is safe.

## 2. Problem statement

A driver changing lanes may misjudge the distance or approach rate of a
vehicle coming from behind. A vehicle that appears far away may still be
closing quickly. The project explores whether a camera and computer
vision can provide an additional warning based on both the separation
distance and the estimated time remaining before the gap closes.

## 3. Aim and objectives

### Aim

To develop a low-cost camera-based software prototype that estimates the
distance and approach risk of a rear vehicle and presents a lane-change
warning.

### Objectives

1.  Capture live video from a camera.
2.  Detect a known ArUco marker attached to the target/test vehicle.
3.  Estimate target distance from the marker's apparent pixel width and
    a calibrated focal length.
4.  Smooth noisy distance measurements.
5.  Estimate closing speed from successive distance readings and
    timestamps.
6.  Calculate TTC when the target is closing sufficiently quickly.
7.  Apply configurable distance and TTC thresholds to classify the
    situation.
8.  Display measurements, warning status and the live camera feed
    through a Flask web interface.
9.  Demonstrate the concept with a controlled toy-car/model-vehicle
    setup.

## 4. System overview and workflow

### 4.1 End-to-end processing sequence

1.  **Camera capture:** OpenCV reads frames from the selected camera
    (`CAMERA_INDEX = 0` in `app.py`).
2.  **Pre-processing:** Each frame is converted from BGR colour to
    grayscale.
3.  **Marker detection:** OpenCV's ArUco detector searches the
    `DICT_4X4_50` dictionary.
4.  **Target selection:** Only marker ID `0` is accepted. Other marker
    IDs are ignored.
5.  **Pixel measurement:** The four marker corners are used to calculate
    all four edge lengths in pixels. Their mean is treated as the
    apparent marker width.
6.  **Distance estimation:** The calibrated pinhole-camera relationship
    estimates distance from the known physical marker width and measured
    pixel width.
7.  **Smoothing:** A rolling history of up to five distance measurements
    is averaged.
8.  **Motion estimation:** Change in distance divided by elapsed time
    estimates closing speed.
9.  **TTC estimation:** If closing speed exceeds the implementation's
    positive threshold, TTC is estimated as distance divided by closing
    speed.
10. **Decision logic:** Distance and TTC are compared with configured
    thresholds. If either limit is crossed, status becomes `UNSAFE`;
    otherwise it becomes `SAFE`. If the marker is absent, status is
    `NO VEHICLE`.
11. **Dashboard update:** Shared status data is updated under a thread
    lock. Flask exposes the values through `/api/status` and streams the
    latest annotated camera frame through `/video_feed`.

### 4.2 Architecture diagram

```text
Camera
  |
  v
OpenCV frame capture
  |
  v
Grayscale conversion
  |
  v
ArUco detection (DICT_4X4_50, ID 0)
  |
  v
Marker corner / apparent-width calculation
  |
  v
Calibrated distance estimation
  |
  v
Five-sample moving average
  |
  v
Closing speed from distance change / elapsed time
  |
  v
TTC estimate
  |
  v
Distance + TTC threshold decision
  |
  v
Shared dashboard data
  |
  +-----------------------+
  |                       |
  v                       v
Flask JSON API         MJPEG video endpoint
  |                       |
  +-----------+-----------+
              |
              v
       Browser dashboard
```

## 5. Technical method and equations

### 5.1 ArUco marker detection

An ArUco marker is a square fiducial marker with a coded black-and-white
pattern. Its identity can be detected in an image, and its four corners
provide a geometric reference. This project uses OpenCV's predefined
`DICT_4X4_50` dictionary and selects marker ID `0`.

The configured physical marker width in `app.py` is
`MARKER_WIDTH = 5.0`, interpreted as centimetres by the distance
calculation. The `marker.py` utility generates a 600-pixel marker image
with ID 0 and adds 100 pixels of white padding on every side.

The physical measurement must refer to the marker's actual coded square,
not the surrounding white padding.

### 5.2 Camera calibration

The distance calculation requires the camera's focal length in pixel units. The calibration utility estimates it using a marker placed at a measured distance.

**Focal-length equation**

```text
f = (p × D) / W
```

Where:

- `f` = focal length in pixels
- `p` = observed marker width in pixels
- `D` = known camera-to-marker distance
- `W` = actual marker width

**Runtime distance equation**

```text
distance = (f × W) / p
```

The estimated distance is in the same physical unit used for `W`. With the project's centimetre convention, distance is reported in centimetres.

**Calibration procedure:**

1. Connect the camera and run `calibrate.py`.
2. Place the marker at a measured, fixed distance from the camera.
3. Wait until the marker is detected.
4. Press `C` to calculate and save `focal_length` in `calibration.json`.
5. Run `app.py` using that calibration file.

### 5.3 Distance smoothing

The runtime application stores the latest five raw distance estimates in a deque and calculates their arithmetic mean.

```text
smoothed_distance = (distance_1 + distance_2 + ... + distance_N) / N
```

Here `N` is the number of available samples, up to five. This reduces frame-to-frame jitter but can introduce some lag when the target moves quickly.

### 5.4 Closing speed

The application estimates closing speed from two consecutive smoothed distance values.

```text
closing_speed = (previous_distance - current_distance) / elapsed_time
```

Where:

- `previous_distance` = previous measured distance
- `current_distance` = current measured distance
- `elapsed_time` = time between the two measurements, in seconds

With distance in centimetres, the result is centimetres per second (`cm/s`). A positive value means the gap is decreasing; a negative value means the gap is increasing. The current implementation calculates TTC only when `closing_speed > 1 cm/s`.

### 5.5 Time to collision (TTC)

For a positive closing speed:

```text
TTC = current_distance / closing_speed
```

With distance in centimetres and closing speed in centimetres per second, TTC is in seconds. The current implementation leaves TTC unavailable (`None`) unless closing speed exceeds `1 cm/s`. This avoids division by zero and avoids reporting a finite TTC when the target is stationary or moving away.

TTC is a simplified constant-relative-speed estimate. It assumes the current closing speed remains approximately constant.

### 5.6 Current backend decision logic

`app.py` defines (can be modified accordingly based on real measurements):

| Parameter           |          Current value | Meaning                                          |
| ------------------- | ---------------------: | ------------------------------------------------ |
| `MARKER_WIDTH`      |                 5.0 cm | Physical marker width assumed by the calculation |
| `MIN_SAFE_DISTANCE` |               100.0 cm | Distance threshold                               |
| `MIN_SAFE_TTC`      |                  3.0 s | TTC threshold                                    |
| `CAMERA_INDEX`      |                      0 | Default camera device index                      |
| Distance history    |              5 samples | Moving-average window                            |
| TTC condition       | closing speed > 1 cm/s | Minimum closing speed for TTC calculation        |

Decision behaviour:

- Marker absent: `NO VEHICLE`.
- Marker detected and distance below 100 cm: `UNSAFE`.
- Otherwise, if TTC is available and below 3 seconds: `UNSAFE`.
- Otherwise: `SAFE`.

The decision rule can be written in plain text as:

```text
UNSAFE = (distance < 100 cm) OR (TTC < 3 seconds)
```

The TTC condition is considered only when TTC is available. These are demonstration thresholds, not validated road-safety limits.

## 6. Software and tools

---

Tool / library Role

---

Python Main programming language and
processing logic

OpenCV (`opencv-contrib-python`) Camera capture, image processing
and ArUco detection

NumPy Numerical and array operations

Flask Local web server, HTML rendering
and HTTP endpoints

HTML Dashboard structure

CSS Dashboard styling and responsive
layout

JavaScript Requests live status data and
updates dashboard elements

JSON Stores calibration and carries
status data to the frontend

Browser Displays the dashboard and camera
stream

---

The repository's `requirements.txt` lists `opencv-contrib-python`,
`numpy` and `flask`.

## 7. Repository structure

The repository contains:

```text
Smart_Side_Mirror/
├── static/              # Frontend static assets (CSS / JavaScript)
├── templates/           # Flask HTML template(s)
├── app.py               # Main Flask application and live processing worker
├── calibrate.py          # Camera focal-length calibration utility
├── calibration.json      # Saved focal-length calibration value
├── marker.py             # Generates ArUco marker ID 0
├── marker.png            # Generated marker image
└── requirements.txt      # Python dependencies
```

### File responsibilities

- **`app.py`** --- Main integrated application. Loads calibration,
  initializes ArUco detection, starts the camera-processing worker,
  calculates distance/closing speed/TTC, updates shared dashboard
  data, and provides Flask routes.
- **`calibrate.py`** --- Captures a marker at a known distance and
  writes the estimated focal length to `calibration.json`.
- **`calibration.json`** --- Stores `focal_length`, loaded by `app.py`
  at startup. It is specific to the camera setup used during
  calibration.
- **`marker.py`** --- Creates an ArUco marker with ID 0 and saves it
  as `marker.png`.
- **`marker.png`** --- Marker to print/display and attach to the model
  target.
- **`templates/`** --- Flask HTML template files.
- **`static/`** --- CSS and JavaScript used by the browser dashboard.
- **`requirements.txt`** --- Python package list.

## 8. Backend and frontend interface

### 8.1 Flask routes

---

Route Method Purpose

---

`/` GET Renders the dashboard
HTML template

`/api/status` GET Returns latest
measurements and
detection status as
JSON

`/video_feed` GET Streams the latest
camera frame as MJPEG

---

The status JSON has this shape:

```json
{
  "distance": 125.4,
  "closing_speed": 18.2,
  "ttc": 6.89,
  "status": "SAFE",
  "detected": true
}
```

The values above are illustrative only, not measured results from the
repository. When no marker is detected, `distance` and `ttc` are `null`,
closing speed is zero, status is `NO VEHICLE`, and `detected` is false.

### 8.2 Dashboard design and interpretation

The dashboard's primary purpose is to make lane-change status
immediately understandable. The latest design direction for the project
is an automotive-style digital instrument cluster: - A prominent central
lane-change-assist status panel. - Large rear-vehicle distance, with
closing speed and TTC as supporting values. - Green styling for the
backend `SAFE` state and red styling for `UNSAFE`. - A distinct
neutral/no-target state when no marker is detected. - A live
camera/mirror feed. - Decorative speedometer and RPM gauges and other
instrument readouts included for cockpit appearance.

**Note:** Speed, RPM, fuel, temperature,
battery, odometer and cruise-control values are decorative/dummy values.

## 9. Setup and execution

### 9.1 Prerequisites

- Computer with Python installed.
- Working webcam or USB camera.
- Repository cloned locally.
- Printed/displayed ArUco marker ID 0 with known physical width.
- Ruler/measuring tape for calibration.
- Clear, well-lit test area and a model/toy vehicle for controlled
  testing.

### 9.2 Create and activate a virtual environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 9.3 Generate the marker if needed

```bash
python marker.py
```

This creates `marker.png` containing ArUco marker ID 0. Print it at a
measured physical size. Avoid resizing it unpredictably after
calibration.

### 9.4 Calibrate the camera

1.  Confirm the actual printed marker width and set `MARKER_WIDTH`
    consistently.
2.  Run:

```bash
python calibrate.py
```

3.  Place the marker at the exact distance specified by the
    script.
4.  Press `C` when the marker is detected.
5.  Confirm `calibration.json` contains a numeric `focal_length`.

### 9.5 Run the integrated application

From the repository root:

```bash
python app.py
```

The backend prints:

```text
http://127.0.0.1:5000
```

Open that address in a browser on the same computer. The backend uses
camera index 0 and starts the camera worker in a daemon thread. If the
intended camera is not index 0, update `CAMERA_INDEX` in `app.py`.

Stop the application from the terminal with `Ctrl+C`.

## 10. Demonstration

Use a controlled tabletop demonstration.

### Demonstration setup

- Main computer running the Flask dashboard.
- Webcam positioned to represent the rear-view/side-mirror camera.
- Toy/model car carrying marker ID 0.
- Measured starting distances and a safe way to move the model car
  toward/away from the camera.
- Dashboard visible to the audience.

## 11. Output

When a marker is visible, the system: - Draws a detection overlay
on the camera frame. - Estimates and displays distance in centimetres. -
Estimates closing speed in centimetres per second. - Displays TTC in
seconds when the target is approaching above the minimum speed
threshold. - Changes the warning state based on the configured distance
and TTC thresholds.

When the marker is absent, the system shows `NO VEHICLE`.

## 12. Future scope

Possible improvements, clearly labelled as future work: - Replace
marker-based detection with a trained vehicle detector (for example, an
appropriate YOLO model) so ordinary vehicles can be detected. - Use
object tracking to maintain target identity across frames. - Estimate
distance using stereo vision, depth cameras, radar, or a more robust
monocular-depth method. - Add lane detection and determine whether the
detected vehicle occupies the target adjacent lane. - Track multiple
vehicles. - Improve TTC estimation
using filtered velocity/acceleration and confidence bounds. - Add
configurable warning levels, audible alerts and left/right
mirror-specific views. - Log timestamped measurements for repeatable
evaluation. - Add camera health checks and visible stale-data
indication. - Conduct systematic accuracy, latency and environmental
testing.

---
