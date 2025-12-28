Vision Development Paths (Historical Record)

This document records the actual vision paths explored during development, what worked, what failed, and why the final approach won.
Nothing here is accidental or wasted — each path informed the next.

Path 1 — Basic Object Recognition (Color Detection)

Goal
Detect an object using the camera and identify it reliably by color.

What was done

Camera capture via IMX708

HSV color space conversion

Color masking

Centroid detection

Major issues encountered

Colors initially appeared inverted / incorrect

Camera color ordering and OpenCV expectations did not match

HSV ranges made no sense until color inversion was fixed

Key fixes

Corrected color channel handling

Verified HSV conversion correctness

Validated mask visually using saved frames

What worked

Stable color masking

Reliable centroid detection

Understanding of HSV behavior under lighting

Why this path was insufficient

Detection alone does not produce motion

No spatial relationship between image and robot

“Seeing” an object does not explain how the robot should move

Outcome

Solid foundation

Vision pipeline validated

Moved on to control integration

Path 2 — Vision-Guided Motion with IK

Goal
Use object position in the camera to directly drive robot motion using inverse kinematics.

What was attempted

Detect object centroid (u, v)

Convert image movement into IK targets

Move robot end effector toward object visually

Problems encountered

Motion felt opaque

It was unclear why the robot moved the way it did

Small image noise caused unpredictable motion

No stable spatial grounding

Core issue

Visual servoing without a reference frame

The robot was reacting to pixels, not geometry

Why this path was abandoned

Difficult to reason about

Hard to debug

Unstable under noise and lighting changes

Outcome

Demonstrated that “vision → IK” can work

But lacked determinism and explainability

Path 3 — Tool & Object Marking (Dual-Color Tracking)

Goal
Track both the tool and the object simultaneously and move until their image coordinates matched.

What was done

Added separate HSV profiles for:

Tool marker

Object marker

Computed centroids for both

Attempted to align tool centroid (u_t, v_t) with object centroid (u_o, v_o)

Why this was better

Relative alignment is more meaningful than absolute pixels

Reduced ambiguity compared to single-object tracking

Robot behavior became more interpretable

Limitations

Still purely image-space

Matching centroids does not guarantee real-world alignment

Sensitive to perspective distortion

Accuracy improved, but not enough

Outcome

Major conceptual improvement

Still not grounded in real geometry

Path 4 — Table Mapping (UV → XY Correlation)

Goal
Map image coordinates (u, v) to real table coordinates (x, y).

What was done

Sampled known points on the table

Recorded corresponding camera UV coordinates

Fit mappings (homography / transformations)

Treated the table as a known plane

Why this worked

Introduced spatial grounding

Pixels became coordinates with meaning

Robot motion became deterministic

Debugging became straightforward

Tradeoffs

Calibration effort

Data collection overhead

Why this path won

Accuracy improved dramatically

Motion became explainable

Noise tolerance increased

Vision stopped “guessing” and started measuring

Outcome

This became the backbone of the final system

Final Path — Safe Step Alignment (AUTHORITATIVE)

What it is

Uses table-mapped coordinates

Moves in small, bounded, explainable steps

Always knows why it is moving

No black-box servoing

Why it beats all previous approaches

Deterministic

Robust

Human-interpretable

Easy to debug

Scales with confidence, not complexity

Final decision

Lesson 08 (Safe Step Alignment) promoted to Lesson 06

All other vision paths archived

Vision calibration centralized in Lesson 03

Key Lessons Learned

Fixing color handling early is critical

HSV calibration must be human-verified

Visual servoing without spatial grounding is fragile

Relative image alignment helps, but geometry wins

Mapping the world beats reacting to pixels

Fewer assumptions → more control

Status

Lesson 03: Vision primitives & calibration (authoritative)

Lesson 06: Vision-guided alignment (authoritative)

Other lessons preserved for historical reference only
