# Vision → IK Servoing (Historical)

This folder contains an experimental approach where object centroids in image
space were used to drive inverse kinematics directly.

## What worked
- Object detection
- Centroid tracking

## Why it was abandoned
- Motion behavior was opaque
- Hard to reason about
- Sensitive to noise

## What it taught
- Vision must be spatially grounded
- Pixels alone are not geometry
