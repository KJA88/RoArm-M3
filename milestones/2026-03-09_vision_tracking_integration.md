# Milestone – Vision Tracking System Integration
Date: 2026-03-09

## Objective
Integrate computer vision tracking with the RoArm-M3 robot.

The goal of this session was to create a working pipeline where a vision
system detects a person and commands the robot base to track them.

---

## System Architecture

Jetson Orin Nano
    │
    │ YOLOv8 person detection
    │ MQTT
    ▼
Raspberry Pi
    │
    │ tracking controller
    ▼
RoArm-M3 Pro

---

## Key Components

### Jetson Vision System
Script:
vision_person_tracker_v2.py

Responsibilities:

- Capture camera frames
- Run YOLOv8 person detection
- Calculate bounding box center
- Publish center X coordinate via MQTT
- Provide live video stream for debugging

MQTT Topic:
robot/track

---

### Raspberry Pi Robot Controller
Script:
runtime/core/person_tracking_base_only.py

Responsibilities:

- Subscribe to robot/track MQTT topic
- Calculate error between detected target and frame center
- Convert error to base rotation command
- Smooth motion using gain and smoothing factors
- Send JSON commands to RoArm via serial

---

## Tracking Algorithm

1. Jetson detects person
2. Bounding box center is computed
3. X coordinate is published over MQTT
4. Raspberry Pi receives coordinate
5. Error relative to frame center is calculated
6. Error is mapped to robot base angle
7. Command is sent to the robot

---

## Control Parameters

FRAME_WIDTH = 640

MAX_BASE = 1.6
MIN_BASE = -1.6

GAIN = 0.7
SMOOTH = 0.2

These parameters control:

- tracking sensitivity
- motion smoothing
- base rotation limits

---

## Hardware Configuration

Camera configuration tested in two modes:

### Eye-to-Hand (Stationary Camera)
Camera mounted above and behind the robot.

Result:
Works and produces smoother tracking.

### Eye-in-Hand (Camera on Arm)
Camera mounted directly on the robot arm.

Result:
Works but can oscillate depending on movement.

---

## Repository Cleanup

During this session the workspace was reorganized.

Robotics workspace structure:

~/robotics
├── roarm-m3
├── jetson-vision
├── dhras-architecture
└── experiments

Inside RoArm repository:

roarm-m3
├── runtime
├── lessons
├── scripts
├── vision
├── docs
├── archive
├── milestones
└── logs

Unused experimental scripts were archived.

---

## Working System Status

Vision detection: working  
MQTT communication: working  
Robot base tracking: working  
Video stream debugging: working  

System successfully tracks a person and rotates the base to follow them.

---

## Next Steps

Planned improvements:

1. Improve tracking stability
2. Implement OpenCV tracker for higher FPS
3. Add search behavior when target is lost
4. Add multi-object tracking
5. Integrate camera calibration
