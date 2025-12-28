Architecture Decisions Record (ADR)

This document records key architectural decisions, the alternatives considered, and the reasoning behind each choice.
The purpose is to prevent revisiting settled questions and to preserve hard-earned understanding.

ADR-001 — Vision Calibration Belongs in Lesson 03

Decision
All vision calibration (HSV creation, sampling methodology) lives exclusively in Lesson 03.

Context
Early versions of the project allowed HSV calibration logic to appear in multiple lessons and tools. This caused duplication, confusion, and inconsistent behavior.

Alternatives Considered

Per-lesson calibration

Runtime calibration inside alignment code

Separate vision tools outside the lesson structure

Why Those Were Rejected

Calibration leaking into application logic caused architectural drift

Runtime calibration made behavior non-deterministic

External tools broke the learning progression

Outcome

Lesson 03 defines all vision primitives

All later lessons load HSV data only

Vision calibration never appears in Lessons 05+

ADR-002 — Fixed Center-Box Sampling Over ROI Selection

Decision
HSV calibration uses a fixed, small center box instead of ROI selection or mouse interaction.

Context
Multiple HSV calibration methods were tested, including ROI selection and region prompts.

Why Center-Box Sampling Won

Headless-safe

Deterministic

Human-verifiable

No UI dependencies

Encourages physical alignment, not software guessing

Outcome

User aligns object physically

Script samples a known, fixed region

Results are reproducible and explainable

ADR-003 — Abandon Direct Vision-to-IK Servoing

Decision
The project does not use direct visual servoing (pixel error → IK motion).

Context
Early attempts moved the robot based directly on image centroid error.

Problems Encountered

Motion felt opaque

Behavior was hard to reason about

Sensitive to noise and lighting

Difficult to debug

Outcome

Vision is treated as a sensor, not a controller

Geometry and spatial grounding are required before motion

ADR-004 — Relative Image Alignment Is Insufficient Alone

Decision
Tracking both tool and object in image space is not sufficient for precise alignment.

Context
Dual-marker tracking improved behavior by aligning centroids of tool and object.

Why It Was Rejected

Still purely image-space

Perspective distortion remains

No guarantee of real-world alignment

Outcome

Relative alignment informed later work

But was replaced by spatial mapping

ADR-005 — Table Mapping (UV → XY) Is Required

Decision
The table surface is explicitly mapped from image coordinates (u, v) to real coordinates (x, y).

Context
Accuracy plateaued when working only in image space.

Why This Won

Introduced spatial grounding

Made motion deterministic

Simplified debugging

Improved accuracy dramatically

Tradeoffs

Calibration effort

Data collection overhead

Outcome

This mapping underpins the final system

Enables safe, explainable motion

ADR-006 — Safe Step Alignment as Final Control Strategy

Decision
Final vision-guided motion uses safe, bounded step alignment, not continuous servoing.

Context
Continuous visual servoing remained fragile under noise.

Why Safe Step Alignment Won

Deterministic

Human-interpretable

Noise tolerant

Easy to reason about

Easy to debug

Outcome

Lesson 08 promoted to Lesson 06

All other vision paths archived

This is the authoritative solution

ADR-007 — Preserve Exploration as Documentation, Not Code

Decision
Explored paths are preserved in documentation and archived folders, not active lessons.

Context
Multiple valid but superseded approaches were explored.

Outcome

Clean, linear codebase

Full historical record preserved

Learning retained without technical debt

Status

Lesson 03: Vision foundation (authoritative)

Lesson 06: Vision-guided alignment (authoritative)

Lessons 05–07: Archived, documented, not executed

End of Record
