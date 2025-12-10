# RoArm-M3-S / M3-Pro – Python Control & Kinematics

This repo is my Python control stack and kinematics lab for the Waveshare RoArm-M3-S / RoArm-M3-Pro robotic arm.

The goals:

- Control the arm over USB serial + JSON from Python (no browser UI needed).
- Have a clear, documented kinematic model matched to this physical arm.
- Keep a permanent engineering log so future work (or another AI) doesn’t redo the same debugging.

---

## 🔧 What this repo actually does

### 1. Simple, safe runtime control

Main daily-use script:

**`roarm_simple_move.py`**

It supports:

- `home` – go to tall “candle” pose  
- `feedback` – print firmware XYZ + joints  
- `goto_xyz` – move to a target XYZ using calibrated planar IK  

Example:

```bash
python3 roarm_simple_move.py home
python3 roarm_simple_move.py goto_xyz 235 0 234
python3 roarm_simple_move.py feedback
```

It uses only:

- T=105 → feedback  
- T=102 → full joint radian control  

The kinematics model is a **shoulder-origin 2-link planar chain + base yaw**, calibrated in `planar_calib.json`.

---

## 🔧 Calibration & Kinematics Tools

Included tools:

- **`roarm_collect_samples_safe.py`**  
  Collect (shoulder, elbow) → (x, z) samples from firmware safely.

- **`roarm_fit_planar.py`**  
  Fit L1, L2, X0, Z0, shoulder_offset, elbow_offset and write `planar_calib.json`.

Related reference files:

- **`roarm_arm_characterization_CALIBRATED.json`**  
  Historical DH snapshot before planar calibration approach.

---

## 🚀 Quick Start

### Virtual environment (optional)

```bash
source ~/.venv/bin/activate
# quit venv:
deactivate
```

### Connect the arm

USB-C → Raspberry Pi (or PC)

Serial device is usually:

```
/dev/ttyUSB0
```

Or stable persistent device:

```
/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_...
```

### Home the arm

```bash
python3 roarm_simple_move.py home
```

### Move to canonical test target

```bash
python3 roarm_simple_move.py goto_xyz 235 0 234
```

Expected behavior:

- IK solution:  
  base ≈ 0.0  
  shoulder ≈ -0.474  
  elbow ≈ 1.973  
- Firmware feedback:  
  x ≈ 237 mm  
  z ≈ 229–230 mm  
- Error:  
  4–5 mm → **PASS**

---

## 📐 FK & IK Math (Hand Calculations)

All math documents are located inside **docs/**:

- `fk_hand_calc_planar.md`
- `fk_2link_planar_handcalc.md`
- `ik_hand_calc_planar.md`
- `ik_2link_planar_handcalc.md`

### The FK model used at runtime:

```
φ   = s + shoulder_offset
e_eff = e + elbow_offset
φ₂  = φ + e_eff

x_p = L1*sin(φ) + L2*sin(φ₂) + X0
z_p = L1*cos(φ) + L2*cos(φ₂) + Z0

x = cos(base)*x_p
y = sin(base)*x_p
z = z_p
```

### The IK solver:

```
base = atan2(y, x)

x_p = hypot(x, y)
x_s = x_p - X0
z_s = z  - Z0

Use law-of-cosines to solve e_eff
Solve φ from triangle geometry

shoulder = φ   - shoulder_offset
elbow    = e_eff - elbow_offset
```

These exactly match the runtime code.

---

## 📊 Planar Model & Calibration Rules

Documented in:

**`docs/runtime_planar_model.md`**

Key facts:

- Firmware (x,y,z) origin is **at the shoulder pitch joint**.  
- Planar model uses six parameters:  
  **L1, L2, X0, Z0, shoulder_offset, elbow_offset**  
- `planar_calib.json` should **ONLY** be rewritten by `roarm_fit_planar.py`.  
- Never hand-edit calibration parameters.

---

## �� Command Cheatsheet

See: **`docs/command_cheatsheet.md`**

Includes:

- VENV activation  
- Home / Goto XYZ commands  
- Torque on/off  
- LED on/off JSON  
- Bash aliases  
- USB serial device ID reminder  
- Direct JSON examples

---

## 🧠 Engineering Log

Two locations:

### 1. `docs/history_issues_and_fixes.md`
Tracks all major issues, including:

- Wrong origin assumption  
- Wrong JSON keys or wrong T codes  
- Calibration failures  
- Fix explanations  

### 2. `docs/roarm_kinematics_control_log.json`
Structured memory file containing:

- Coordinate frame rules  
- Joint sign conventions  
- Calibration parameters  
- Canonical test target definition  
- Rules for future maintainers  

This ensures the entire story of the project is preserved.

---

## 📂 Repository Layout (cleaned)

```
README.md
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
```

Everything in `archive/` is preserved code that is not used in production.

---

## ⚠️ Safety Notes

- Avoid **z < 150 mm** except controlled testing  
- Avoid gripper **g < 1.1 rad** (servo stall risk)  
- Always home before sending new commands  
- Keep the USB cable slack  
- Monitor shoulder & elbow when approaching limits  

---

## 🎯 Purpose of This Repo

This repo demonstrates:

- Real robotic arm control over UART/JSON  
- A documented and validated kinematic model  
- A repeatable calibration pipeline  
- A professional structure suitable for jobs/portfolio  
- Clear logs so future work doesn’t break working code  

Another engineer (or another AI) can now read this repo and continue development safely.

---

## 📄 License

Recommended: MIT License (add LICENSE file later).

