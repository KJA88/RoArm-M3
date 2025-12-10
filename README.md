START OF README.md
RoArm-M3-S / M3-Pro — Python Control & Kinematic Calibration

This repository contains my complete Python-based control stack for the Waveshare RoArm-M3-S / RoArm-M3-Pro robotic arm. The goal is accurate, safe, and fully documented multi-axis control over UART/JSON, including kinematics, calibration, and high-level motion.

This project is built to demonstrate:

Real robotics engineering workflows

Clear kinematic modeling with documentation

A reproducible calibration pipeline

Clean, portfolio-quality engineering style

Code that another engineer or AI assistant can safely continue

Features
Python UART Control Layer

Safe and consistent Python communication with:

pyserial over /dev/ttyUSB0

Auto-formatted JSON commands

Safe joint-limit enforcement

Supported official commands:

T=101 : single-joint radian move

T=102 : full 6-joint radian move

T=104 : XYZ blocking inverse kinematics move

T=105 : feedback returns joints, torques, XYZ

T=210 : torque lock on/off

T=114 : LED control

The canonical safe control script is:
roarm_simple_move.py

Commands provided:

home

feedback

goto_xyz X Y Z [--refine]

Kinematics and Calibration Model

This project implements:

Forward kinematics (FK) for a shoulder-origin robot

Inverse kinematics (IK) for shoulder + elbow + base

A full planar calibration model for:

Link 1 length

Link 2 length

X/Z offsets

Shoulder and elbow radian offsets

All math is thoroughly documented in the docs/ directory:

fk_hand_calc_planar.md

ik_hand_calc_planar.md

fk_2link_planar_handcalc.md

ik_2link_planar_handcalc.md

runtime_planar_model.md

roarm_kinematics_control_log.json

history_issues_and_fixes.md

command_cheatsheet.md

The major discovery (and root of 90% of early confusion):
Firmware XYZ origin is at the SHOULDER joint, not the base.

This repo contains all experiments, tests, and logic that proved this and rebuilt the model correctly.

Calibration Tools

Two-stage calibration appears in this repository:

Planar model fitting
Scripts:

roarm_collect_samples_safe.py

roarm_fit_planar.py

Output is written to:
planar_calib.json

These values must not be manually edited.
They are updated only through the fitter.

(Future) Jacobian refinement
Currently disabled because plain IK already provides around 5 mm accuracy, enough for camera-guided picking.

Canonical High-Level Usage

Home the robot:
python3 roarm_simple_move.py home

Move to XYZ:
python3 roarm_simple_move.py goto_xyz 235 0 234

Get live feedback:
python3 roarm_simple_move.py feedback

Torque off:
python3 torque_off.py

LED on:
python3 serial_simple_ctrl.py /dev/ttyUSB0 '{"T":114,"led":255}'

Repository Structure

roarm_simple_move.py - Main safe interface
roarm_collect_samples_safe.py - Collects calibration samples
roarm_fit_planar.py - Fits planar calibration model
planar_calib.json - Latest calibrated values
roarm_kinematics_control_log.json - Ground-truth engineering log
docs/ - All FK/IK math and history
archive/ - Old unused experiments
README.md - This file

Safety Rules

Never command Z below 150 mm unless testing very carefully.

Gripper angle g below 1.1 rad risks servo stall.

Always run home before experiments.

Keep the USB cable slack so the arm doesn’t yank the port.

Engineering Log

All reasoning, modeling, calibration, failures, and fixes are permanently stored here:

docs/history_issues_and_fixes.md
docs/roarm_kinematics_control_log.json

These documents prevent knowledge regression and ensure future changes do not break confirmed truths.

Project Intent

This repository demonstrates:

Real robotic arm control over UART

Clear FK/IK modeling with human-readable math

A structured calibration system

A professional-level robotics software structure

A foundation for AI-based pick-and-place control

License

MIT License (or your preferred choice)

===========================================================
END OF README.md
