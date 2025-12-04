RoArm-M3-S / M3-Pro Python Control Project

This repository contains my work building a complete Python-based control stack for the Waveshare RoArm-M3-S / RoArm-M3-Pro robotic arm.
It includes serial communication, JSON-command control, motion control tools, inverse kinematics experiments, and mission-file automation.

The goal of this project is to develop full 6-axis programmatic control of the robotic arm using standard Python and UART, without relying on the browser interface.

✨ Features
✓ Python UART Control

Uses pyserial to communicate with the arm over USB-UART.
Implements the protocol described in Waveshare’s documentation and supports both sending commands and reading async feedback from the arm.
Based on the official demo serial_simple_ctrl.py.


✓ JSON Command Interface

All arm movement is performed through Waveshare’s JSON instructions, including:

T=101 – single-joint radian control

T=102 – full 6-joint radian control

T=103 / T=104 / T=1041 – inverse kinematics (XYZT) control

T=105 – live feedback of all joint positions, loads, and end-effector coordinates

T=210 – torque lock on/off

T=114 – LED control

Full JSON command descriptions come from the Waveshare tutorial.



✓ Mission File Recording & Playback

Implements tools for:

Creating mission files

Appending JSON movement steps

Inserting, replacing, or deleting steps

Recording the robot’s current pose directly into mission steps

Looping mission playback

Based on Waveshare’s mission-editing JSON interface.


✓ Inverse Kinematics Work (Custom)

Includes experiments using SciPy’s least_squares optimizer to solve for:

Base, shoulder, elbow, and wrist pitch joint angles

Forward kinematics model (FK)

Safe joint limits

Pose solving for X/Y/Z targets

These scripts form the foundation for higher-level autonomous motion.

✓ Safety Tools

Utility code for:

Torque-off operations

Joint-limit enforcement

Safe claw calibration (avoiding servo stall)

Smooth motion profiles through speed (spd) and acceleration (acc) fields

📁 Repository Structure
/python/
    serial_ctrl/       # UART communication scripts
    ik/                # Inverse kinematics solvers and FK models
    utils/             # Safety, presets, calibration, logging
missions/
    *.mission          # Example mission files created on the robot
docs/
    README.md          # This document

🔧 Requirements

Python 3.10+

pyserial

numpy

scipy (for IK)

Optional: requests (for Wi-Fi HTTP control mode)

Install:

pip install -r requirements.txt

🚀 Quick Start
1. Connect the Robotic Arm

Plug Type-C into PC (Windows, Linux, Raspberry Pi, Jetson, etc.).

2. Launch the UART controller
python serial_simple_ctrl.py COM3      # Windows
python serial_simple_ctrl.py /dev/ttyUSB0   # Linux

3. Send a command

Move the arm to an initial pose:

{"T":100}


Move joints individually:

{"T":101,"joint":2,"rad":0.5,"spd":0,"acc":10}


Move using full 6-joint radian control:

{"T":102,"base":0,"shoulder":0.6,"elbow":1.2,"wrist":0,"roll":0,"hand":2.5,"spd":0,"acc":10}


Move using inverse kinematics:

{"T":104,"x":235,"y":0,"z":220,"t":0,"r":0,"g":3.14,"spd":0.25}


Turn torque off (free-move):

{"T":210,"cmd":0}

🎥 Mission File Example

Create a mission:

{"T":220,"name":"pick_and_place","intro":"Demo mission"}


Append movement:

{"T":222,"name":"pick_and_place","step":"{\"T\":104,\"x\":200,\"y\":0,\"z\":150,\"t\":0,\"r\":0,\"g\":3.14,\"spd\":0.25}"}


Playback:

{"T":242,"name":"pick_and_place","times":3}


(Documentation source: Step Recording and Reproduction)


📚 Documentation Sources

This project implements control systems based on the official Waveshare documentation:

Robotic Arm Motion Control (JSON command meaning)


Step Recording & Reproduction


Python UART Communication Demo


JSON Command Meaning Overview


🛠 Status

Active development.
Upcoming features:

Full 6-DOF IK including wrist roll & gripper orientation

Smoother Cartesian path planning

Visualizer integration

Web-API wrapper around JSON commands

Object-oriented Python SDK

🤝 Contributions

Pull requests are welcome—especially improvements to IK accuracy, safety constraints, and higher-level motion planning.

📜 License

MIT License (or specify your preferred license).
