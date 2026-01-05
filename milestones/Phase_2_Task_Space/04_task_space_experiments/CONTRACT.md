# Milestone 04: Task-Space Contract

This document defines the authoritative semantic meaning of task-space commands
for the RoArm-M3-S system.

This is a **definition-only contract**.
No enforcement, validation, or motion logic is permitted at this milestone.

---

## 1. Coordinate Definitions (SDK Frame)

The SDK Task Frame is defined by the RoArm-M3 firmware and treated as an external,
opaque reference frame.

- **Origin (0,0,0):** Center of the base at table level.
- **X:** Forward reach (millimeters).
- **Y:** Lateral swing (millimeters).
- **Z:** Vertical height (millimeters).
- **Pitch:** Wrist angle (radians).

Units are fixed and non-negotiable:
- Distance: millimeters (mm)
- Rotation: radians (rad)

---

## 2. Pose Schema (The Grammar)

A Pose Request is only valid if it is expressed as a complete, explicit data structure.

Canonical form:
{ x, y, z, p }

Rules:
- No implicit defaults
- No missing fields
- No relative movements
- All coordinates are absolute in the SDK Task Frame

Any request that violates these rules is invalid by definition.

---

## 3. Reference Boundaries (Static Truths)

These values define the intended operating volume of task-space requests.
They are **declared but not enforced** at this milestone.

- X (Reach):   [150, 480] mm
- Y (Swing):   [-400, 400] mm
- Z (Height):  [20, 500] mm
- Pitch:       [-1.57, 1.57] rad

---

## 4. Explicit Non-Responsibilities

This milestone does NOT:
- Enforce boundaries
- Reject pose requests
- Validate reachability
- Invoke firmware IK
- Move hardware
- Protect the arm

Those behaviors are defined in later milestones.

---

## 5. Contract Status

This document is the **Source of Truth** for task-space semantics.
All subsequent milestones must conform to this contract.

Changes require explicit revision and re-freezing.
