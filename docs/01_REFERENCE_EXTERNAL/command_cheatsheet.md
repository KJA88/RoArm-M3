# RoArm-M3S Command Cheatsheet  
**Canonical Quick-Reference for Real-Arm Operation, Debugging, Calibration & Scripting**  
_Last updated: 2025-12-09_

---

# ============================================================
# 1. PYTHON VENV
# ============================================================

### ▶ Enter venv
```
source ~/.venv/bin/activate
```

### ▶ Exit venv
```
deactivate
```

---

# ============================================================
# 2. SIMPLE UI (manual XYZ mover)
# ============================================================

```
python3 simple_ui.py
```

Prompts for:
```
X Y Z R G
```
- X,Y,Z = mm  
- R = wrist pitch (rad)  
- G = gripper (rad)

---

# ============================================================
# 3. WHY "chmod +x"?
# ============================================================

Makes a Python file executable from the command line:

```
chmod +x my_script.py
```

Allows running:

```
./my_script.py
```

instead of:

```
python3 my_script.py
```

Not required, but convenient.

---

# ============================================================
# 4. POSE CAPTURE → DH SOLVER (LEGACY SYSTEM)
# ============================================================

> **NOTE:** This is legacy material from your original DH solver system  
> BEFORE you switched to the new planar calibration model.

### Clear previous poses
```
rm ~/RoArm/poses.json
```

### Capture poses
```
python3 pose_creator.py
```

### Solve DH parameters
```
python3 dh_solver.py
```

Pipeline summary:
```
pose capture
 → least_squares optimization
 → calibrated_dh.json
 → FK engine (fk.py)
 → IK engine (ik.py)
 → robot motion
```

**IMPORTANT:**  
This entire DH pipeline is **retired** now that you use the **planar calibration (planar_calib.json)** system.

---

# ============================================================
# 5. REBOOT ARM
# ============================================================

### ▶ Using the reboot script
```
python3 reboot_arm.py
```

### ▶ Using raw JSON
```
{"T":999}
```

---

# ============================================================
# 6. TORQUE CONTROL
# ============================================================

### ▶ Torque OFF
```
python3 torque_off.py
```

Raw JSON:
```
{"T":210}
```

### ▶ Torque ON
```
{"T":210,"cmd":1}
```

---

# ============================================================
# 7. DH REFERENCE POSE (LEGACY)
# ============================================================

Raw JSON example:
```
{"T":102,"base":0,"shoulder":1.50,"elbow":0,"wrist":0,"roll":0,"hand":1.0,"spd":0,"acc":0}
```

Script:
```
python3 - << "EOF"
import serial, time
s = serial.Serial('/dev/ttyUSB0',115200,timeout=1)
s.setRTS(False); s.setDTR(False)
s.write(b'{"T":102,"base":0,"shoulder":1.50,"elbow":0,"wrist":0,"roll":0,"hand":1.0,"spd":0,"acc":0}\n')
print("Sent DH reference pose.")
s.close()
EOF
```

---

# ============================================================
# 8. CANDLE POSE (USE THIS NOW)
# ============================================================

### ▶ SAFE Home/Candle Pose
```
python3 roarm_simple_move.py home
```

This is the new standard; replaces DH reference pose.

---

# ============================================================
# 9. LED CONTROL
# ============================================================

### ▶ LED ON
```
python3 led_on.py
```

Raw JSON:
```
{"T":114,"led":255}
```

Direct code:
```
python3 - << 'EOF'
import serial, time
s = serial.Serial("/dev/ttyUSB0",115200,timeout=1)
s.write(b'{"T":114,"led":255}\n')
print("LED ON")
s.close()
EOF
```

### ▶ LED OFF
```
python3 led_off.py
```

Raw JSON:
```
{"T":114,"led":0}
```

---

# ============================================================
# 10. BASH ALIASES
# ============================================================

### Edit ~/.bashrc
```
nano ~/.bashrc
```

### Reload after editing
```
source ~/.bashrc
```

### Example alias
```
alias led_off='python3 ~/RoArm/led_off.py'
```

### Check existing aliases
```
grep -i roarm ~/.bashrc
```

---

# ============================================================
# 11. roarm_simple_move.py (CURRENT, SAFE INTERFACE)
# ============================================================

### ▶ Feedback
```
python3 roarm_simple_move.py feedback
```

### ▶ Home (candle pose)
```
python3 roarm_simple_move.py home
```

### ▶ Move to XYZ
```
python3 roarm_simple_move.py goto_xyz 235 0 234
```

### ▶ With refine attempt (simple refine only)
```
python3 roarm_simple_move.py goto_xyz 235 0 234 --refine --iters 2 --gain 0.35 --settle 6.0
```

**Accuracy expectation:**
- Plain IK error ≈ 4–6 mm  
- Refine (current version) = no improvement (kept intentionally simple)

---

# ============================================================
# 12. PLANAR CALIBRATION SYSTEM (CURRENT)
# ============================================================

Your active model lives in:

```
planar_calib.json
```

Keys:
```
L1
L2
X0
Z0
shoulder_offset
elbow_offset
```

### To recalibrate:

1) Collect samples:
```
python3 roarm_collect_samples_safe.py
```

2) Fit model:
```
python3 roarm_fit_planar.py samples_safe.csv
```

3) Replace planar_calib.json with the fitted file.

**RULES:**
- Do NOT hand-edit planar_calib.json  
- Always refit all values together  

---

# ============================================================
# 13. USB SERIAL DEVICE IDENTIFICATION
# ============================================================

```
/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_5c6dc8363f01f01180d7c1295c2a50c9-if00-port0
```

Use this when the device jumps between ttyUSB0 / ttyUSB1.

---

# ============================================================
# 14. WHAT IS CURRENT VS LEGACY?
# ============================================================

### ✅ **Use these NOW**
- roarm_simple_move.py  
- planar_calib.json  
- torque_off.py / torque_on.py  
- serial_simple_ctrl.py  
- simple_ui.py  
- shoulder-origin FK/IK model  
- history_issues_and_fixes.md  
- runtime_planar_model.md  

### ❌ LEGACY (do not depend on)
- pose_creator.py  
- dh_solver.py  
- calibrated_dh.json  
- fk.py / ik.py (DH version)  
- old DH reference pose  

These can stay in the repo but **not used for new development**.

---

# ============================================================
# 15. CANONICAL TEST POSE (DO NOT CHANGE)
# ============================================================

### Command:
```
python3 roarm_simple_move.py home
python3 roarm_simple_move.py goto_xyz 235 0 234
```

### Expected:
- IK → base=0, shoulder≈−0.4738, elbow≈1.9725  
- Firmware → around x≈237 mm, z≈230 mm  
- Error → 4–6 mm (PASS)

This test verifies you didn't break kinematics.

---

# END OF FILE
