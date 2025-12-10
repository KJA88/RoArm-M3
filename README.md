RoArm-M3-S / M3-Pro – Python Control & Kinematics

This repo is my Python control stack and kinematics laboratory for the Waveshare RoArm-M3-S / RoArm-M3-Pro robotic arm.

The goals:

Control the arm using Python over USB serial + JSON (no browser UI required)

Maintain a clean, correct, documented kinematic model

Keep an engineering log so future work (or another AI) can build on this safely

Provide a portfolio-quality robotics project

🔧 What This Repo Actually Does
1. Simple, Safe Runtime Control

Main daily-use script:

roarm_simple_move.py

It supports:

home → go to tall “candle” pose

feedback → print firmware XYZ + joints

goto_xyz → move to XYZ using calibrated planar IK

Example:

python3 roarm_simple_move.py home
python3 roarm_simple_move.py goto_xyz 235 0 234
python3 roarm_simple_move.py feedback

Commands used internally:

T=105 → firmware feedback

T=102 → full joint radian control

Kinematic model: a shoulder-origin 2-link planar chain + base yaw using calibrated parameters from planar_calib.json.

🔧 Calibration & Kinematics Tools

roarm_collect_samples_safe.py
• Collects (shoulder, elbow) → (x, z) samples safely from the real arm.

roarm_fit_planar.py
• Fits the planar model parameters:
L1, L2, X0, Z0, shoulder_offset, elbow_offset
and writes them into planar_calib.json.

DO NOT edit planar_calib.json by hand.

Historical files:
• roarm_arm_characterization_CALIBRATED.json
(Old DH-based calibration before adopting planar calibration)

🚀 Quick Start
Virtual environment (optional)

source ~/.venv/bin/activate
deactivate

Connect the arm

USB-C to Raspberry Pi or PC

Typical device:
/dev/ttyUSB0

Stable persistent ID:
/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_...

Home the arm

python3 roarm_simple_move.py home

Canonical test target

python3 roarm_simple_move.py goto_xyz 235 0 234

Expected:

IK:
base ≈ 0
shoulder ≈ -0.474
elbow ≈ 1.973

Firmware:
x ≈ 237
z ≈ 229–230

Error ≈ 5 mm → PASS

📐 FK & IK Math (Hand Calculations)

Full documentation located in docs/:

fk_hand_calc_planar.md
fk_2link_planar_handcalc.md
ik_hand_calc_planar.md
ik_2link_planar_handcalc.md

FK used at runtime:

φ = shoulder + shoulder_offset
e_eff = elbow + elbow_offset
φ₂ = φ + e_eff

x_p = L1sin(φ) + L2sin(φ₂) + X0
z_p = L1cos(φ) + L2cos(φ₂) + Z0

x = cos(base)*x_p
y = sin(base)*x_p
z = z_p

IK used at runtime:

base = atan2(y, x)

x_p = hypot(x, y)
x_s = x_p - X0
z_s = z - Z0

Use law-of-cosines → solve e_eff
Solve φ from triangle geometry

shoulder = φ - shoulder_offset
elbow = e_eff - elbow_offset

📊 Planar Model & Calibration Rules

Documented in docs/runtime_planar_model.md

Key rules:

• Firmware XYZ origin is at the shoulder pitch axis, NOT the base
• Planar parameters =
L1, L2, X0, Z0, shoulder_offset, elbow_offset
• planar_calib.json is ONLY rewritten by roarm_fit_planar.py
• Do NOT hand-edit calibration parameters

🧾 Command Cheatsheet

See docs/command_cheatsheet.md

Includes:

• Home / goto_xyz commands
• Torque off/on
• LED on/off JSON
• Bash aliases
• USB device reminders
• Direct JSON examples
• Venv activation commands

🧠 Engineering Log

Two files store the long-term technical memory:

docs/history_issues_and_fixes.md
– Wrong origin assumptions
– JSON protocol mistakes
– Calibration errors
– Fix explanations

docs/roarm_kinematics_control_log.json
– Coordinate frame rules
– Joint sign conventions
– Calibration values
– Canonical test target
– Rules to avoid regressions

This ensures future work never repeats old mistakes.

📂 Repository Layout (Cleaned)

README.md
LICENSE
requirements.txt
planar_calib.json
calibrated_dh.json
roarm_arm_characterization_CALIBRATED.json
roarm_simple_move.py
roarm_collect_samples_safe.py
roarm_fit_planar.py
serial_simple_ctrl.py
torque_off.py
torque_on.py
docs/
archive/

archive/ contains old or unused scripts safely stored.

⚠️ Safety Notes

• Avoid z < 150 mm unless testing slowly
• Gripper below g = 1.1 rad risks servo stall
• Always home before new IK targets
• Keep cable slack (avoid disconnects)
• Watch shoulder/elbow limits

🎯 Purpose of This Repo

This project demonstrates:

• Real robot control via Python → UART → JSON
• A validated and documented kinematic model
• A reproducible calibration pipeline
• A professional structure suitable for jobs/portfolio
• A complete engineering history so progress is never lost

Engineers (or AI) can read this repo and continue development safely.

📄 License
MIT License (see LICENSE)
✅ END OF FILE
