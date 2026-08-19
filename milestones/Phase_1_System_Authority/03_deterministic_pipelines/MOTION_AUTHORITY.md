# RoArm Motion Authority V1

## Current System Phase

The earlier Phase 1 read-only restriction was a development-stage boundary.

That historical restriction remains true for the existing state-inspection
and proposal-validation tools, but it no longer describes the entire RoArm
MCP system.

The project now contains one deliberately approved live-motion path.

## Approved Live Motion

Current approved routine:

`run_lissajous`

Underlying implementation:

`lessons/01_trajectory_and_gripper/demo_lissajous.py`

The underlying routine was separately exercised locally on the physical
RoArm before being exposed through MCP.

## Authority Boundary

Live Lissajous execution must pass through:

`milestone_03_motion_authority.py`

Required conditions:

1. RoArm controller is connected.
2. T:105 state feedback is fresh.
3. Motion request is specifically for the approved Lissajous routine.
4. The local operator has armed a one-shot authorization.
5. Authorization is no older than 120 seconds.
6. SHA-256 of the executed script matches the locally authorized script.
7. No other motion routine currently holds the motion lock.
8. Authorization is consumed before physical movement starts.
9. Authorization, motion start, and motion result are logged.

## Local Operator Authorization

The operator physically present with the RoArm arms one execution with:

`roarm-arm-lissajous`

Remote AI clients cannot create this authorization.

After one motion attempt the authorization is consumed.

## Explicitly NOT Authorized

Motion Authority V1 does not authorize:

- arbitrary joint targets
- arbitrary Cartesian targets
- arbitrary trajectories
- unrestricted serial commands
- unrestricted torque control
- unrestricted gripper control

These require separate future authority definitions.

## Existing Read-Only Tools

The following remain read-only/dry-run:

- get_roarm_status
- get_current_pose
- get_joint_positions
- get_joint_limits
- get_controller_status
- validate_roarm_joint_proposal
- validate_roarm_state_aware_joint_proposal

Their `hardware_action: NONE` behavior remains intentional.

## Authority Precedence

This document and `milestone_03_motion_authority.py` describe the current
motion-authority state of the project.

Earlier Session 28 and early Session 29 documentation describing the whole
RoArm MCP as read-only documents the system at that earlier development
stage and does not supersede this current authority layer.
