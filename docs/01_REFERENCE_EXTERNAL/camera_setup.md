=== START DOC ===
RoArm Vision & Camera Setup Log
--------------------------------

1) Hardware & Physical Setup
----------------------------

- Board: Raspberry Pi 5
- Camera: Arducam / Raspberry Pi Camera Module 3 (IMX708, 12 MP)
- Connection path:
  - IMX708 camera PCB → Arducam 22-pin adapter board
  - 22-pin FFC into adapter
  - 15-pin end of adapter into Pi 5 CSI camera port
- Pi location: Pi 5 is on the desk.
- Camera location: Camera is on the table pointed at the RoArm and workspace.
- Configuration type: "Eye-to-hand" (camera fixed in the world, arm moves in view).

2) OS / System Configuration
----------------------------

- OS: Raspberry Pi OS Bookworm (with rpicam-apps and libcamera installed).

Verified camera tools with:

  rpicam-still --version
  (Output shows something like: rpicam-apps build: v1.10.1 ...)

2.1) /boot/firmware/config.txt changes (Pi 5)
---------------------------------------------

Edited the Pi 5 firmware config to explicitly enable the IMX708 sensor.

Command used:

  sudo nano /boot/firmware/config.txt

Changes made inside that file:

  camera_auto_detect=0      # was 1 before

  [all]
  dtoverlay=imx708          # added line for IMX708 camera

After editing, the Pi was rebooted so the changes take effect:

  sudo reboot

3) Basic Camera Sanity Checks
-----------------------------

After reboot, confirmed that the camera is visible to the system:

  rpicam-still --list-cameras

Expected output example:

  Available cameras
  -----------------
  0 : imx708 [4608x2592 10-bit RGGB] (/base/axi/pcie@.../imx708@1a)
      Modes: ...

Simple still capture test:

  rpicam-still -t 2000 -o test.jpg
  ls test.jpg

Result: test.jpg exists and is a valid image.

Conclusion:
- Camera wiring is correct.
- IMX708 overlay is working.
- rpicam-apps pipeline is functioning.

4) Python Camera Scripts in ~/RoArm
-----------------------------------

All scripts below live in the RoArm repo root:

  ~/RoArm/camera_snap.py
  ~/RoArm/color_detect_snap.py

They use Picamera2 plus OpenCV.

4.1) camera_snap.py — single frame capture
------------------------------------------

Purpose:
- Capture one full-resolution frame from the IMX708 and save it as frame.jpg.

High-level behavior:
- Creates a Picamera2 instance.
- Configures a 4608x2592 BGR stream.
- Captures a single frame as a NumPy array.
- Prints the frame shape (around (2592, 4608, 3)).
- Saves the frame as frame.jpg in the repo root.

Usage:

  cd ~/RoArm
  python3 camera_snap.py
  ls frame.jpg

Observation:
- Script prints the frame shape and "Done."
- frame.jpg appears and can be opened (for example, from VS Code on the PC).

This script is the basic building block for vision debugging (exposure, framing, field of view).

4.2) color_detect_snap.py — simple color blob detection
-------------------------------------------------------

Purpose:
- Capture a frame, run a color mask, find the largest colored blob, and mark its center in an output image.

Pipeline:
- Capture a single frame from the IMX708 via Picamera2.
- Resize the frame down (for speed).
- Convert from BGR to HSV color space.
- Apply an HSV threshold to isolate a chosen color range.
- Find contours in the binary mask.
- Choose the largest contour by area.
- Compute its centroid (cx, cy).
- Draw a green crosshair at (cx, cy) on the resized image.
- Save the annotated image to color_detect_out.jpg.

Usage:

  cd ~/RoArm
  python3 color_detect_snap.py
  ls color_detect_out.jpg

Typical console output:

  Frame shape: (2592, 4608, 3)
  Largest contour area: <some value>
  Detected object at (cx, cy) = (row, col in resized image)
  Approx. full-res coordinates: (x_full, y_full)
  Saved debug image with marker to color_detect_out.jpg
  Done.

Notes:
- color_detect_out.jpg shows the scene with a green cross marking the detected blob center.
- Right now the HSV range is loose, so it may pick up background objects (like picture frames) instead of the intended object.
- This file is the starting point for future work where pixel coordinates will drive robot motion.

5) Current Physical Vision Setup Snapshot
-----------------------------------------

- Camera is not mounted on the arm yet.
- It is placed on the table aimed toward the RoArm and the workspace.
- This is an eye-to-hand camera (fixed relative to the desk, not moving with the arm).
- Captured images include:
  - RoArm vertical column and links.
  - Background items (walls, frames, fan, etc.).

We have verified:
- rpicam-still detects the IMX708.
- camera_snap.py captures a usable frame.
- color_detect_snap.py finds a large color region and marks it.
- frame.jpg and color_detect_out.jpg can be viewed from VS Code running on the host PC while connected to the Pi.

6) Relation to Robot Control (Future Plan)
------------------------------------------

Goal:
- Use the camera to guide the RoArm (vision-based control).

Rough roadmap:
1. Use color_detect_snap.py (or a refined version) to consistently get a robust pixel coordinate (cx, cy) for:
   - A colored object on the table, or
   - The blue plastic of the RoArm itself.

2. At the same time, use the RoArm JSON feedback command:

     {"T":105}

   which returns a feedback packet like:

     {"T":1051,"x":...,"y":...,"z":...,"tit":...,"b":...,"s":...,"e":...,"t":...,"r":...,"g":...}

   This gives the current end-effector coordinates (x, y, z).

3. Log paired data:
   - (cx, cy) from the camera,
   - (x, y, z) from the T=1051 feedback.

4. Use that data later to build an intuitive mapping from image space to robot workspace.

5. Once the mapping is understood, use the RoArm T=1041 "direct coordinate" command to build behaviors like:
   - If the object appears left in the image, nudging the arm left in X/Y.
   - Centering the arm above the detected blob.
   - Eventually, full pick-and-place (vision-guided).

7) Summary / Reset Instructions
-------------------------------

If everything gets wiped and you need to rebuild the vision setup, the minimum steps are:

1. Wire the IMX708 using the adapter:
   - Camera PCB → Arducam 22-pin adapter → Pi 5 CSI port.

2. Edit /boot/firmware/config.txt:

   - Set:
       camera_auto_detect=0
   - Under [all], add:
       dtoverlay=imx708

3. Reboot:

   - sudo reboot

4. Confirm the camera is detected:

   - rpicam-still --list-cameras
   - rpicam-still -t 2000 -o test.jpg

5. In ~/RoArm, ensure these files exist and run:

   - python3 camera_snap.py
   - python3 color_detect_snap.py

6. Check that:
   - frame.jpg exists and looks correct.
   - color_detect_out.jpg exists and shows the camera view with a green cross at the detected blob.

Once all of this works, the Pi camera and basic color detection pipeline are successfully restored and ready to integrate with RoArm motion control.
=== END DOC ===
