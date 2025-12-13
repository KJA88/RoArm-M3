## Lesson 03 – Vision: Color-Based Object Detection (IMX708)

This lesson builds a small, reusable pipeline to:

1. Capture a still image from the IMX708 camera.
2. Calibrate the color of a target object from a center patch.
3. Detect that object in a new frame and return its pixel position `(u, v)`.

All commands are run from the repo root:

    cd ~/RoArm

---

### 1. Capture a still frame

Put the target object roughly in the center of the camera view (e.g., blue vacuum or red cylinder), then:

    python3 lessons/03_vision_color_detection/camera_snap.py

Outputs:

- `frame.jpg` – raw BGR image from the camera.

---

### 2. Calibrate the object’s color (HSV) from the center patch

    python3 lessons/03_vision_color_detection/inspect_center_hsv.py

This script:

- Takes a small patch around the image center.
- Converts it to HSV and computes statistics.
- Draws the sampled patch and center cross:

  - `frame_with_patch.jpg` – original frame with:
    - Green rectangle = sampled patch.
    - Blue cross = image center.

- Writes the HSV range to:

  - `hsv_config.json` – contains:

        {
          "lower": [Hmin, Smin, Vmin],
          "upper": [Hmax, Smax, Vmax]
        }

> Make sure the green rectangle lies mostly on the object you care about.  
> If not, reposition the object, re-run `camera_snap.py`, then `inspect_center_hsv.py`.

---

### 3. Detect the calibrated object and get `(u, v)`

    python3 lessons/03_vision_color_detection/camera_color_localize_picam2.py

This script:

- Loads `hsv_config.json`.
- Captures a new frame from the camera.
- Builds an HSV mask and finds the largest blob of that color.
- Prints the object’s centroid in pixel coordinates:

      Centroid pixel (u, v) = (u_val, v_val)

- Saves debug images:

  - `cam_live_frame.jpg` – raw camera frame.
  - `cam_live_mask.jpg` – binary mask (white = detected color).
  - `cam_live_annotated.jpg` –:
    - Green contour = detected object blob.
    - Red dot = centroid `(u, v)`.
    - Blue cross = image center.

---

### 4. (Optional) Single camera+robot sample

`cam_robot_sample_once.py` is a helper for the next lesson. It is intended to:

- Read the object’s pixel location `(u, v)` using the same HSV pipeline.
- Query the robot for its current end-effector pose `(x, y, z)`.
- Print a single combined sample.

This will be extended later into a logger that builds a dataset of `(u, v, x, y, z)` pairs for camera→robot calibration.
