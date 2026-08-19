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

---

# Constrained Single-Joint Motion V1

## Current Approved Parameterized Motion

The project now contains a deliberately bounded parameterized
live-motion path:

`move_constrained_joint(joint, target_rad)`

Allowed joints:

- `shoulder`
- `elbow`
- `wrist`

Exactly one joint may be targeted per call.

The implementation is:

`milestone_03_joint_motion_authority.py`

## Existing Authority Reused

This live-motion path does not invent new mechanical limits.

It delegates target validation to the existing state-aware
proposal validator and therefore uses the human-verified
Milestone 02 limits.

Current authoritative limits:

- Shoulder: -1.300 to +1.100 rad
- Elbow: -0.366 to +2.734 rad
- Wrist: -1.000 to +1.400 rad

The known DH reference that uses shoulder +1.50 rad remains an
unresolved discrepancy and does NOT override the current
human-verified +1.100 rad authority.

The observed cable pinch near elbow -0.4 rad remains consistent
with retaining the current -0.366 rad elbow minimum.

## Command Behavior

The live command uses the same partial T:102 pattern used by the
authoritative Milestone 02 joint-limit calibration code.

Only the selected joint field is transmitted.

Base, roll, hand/gripper, and other joints are not referenced or reset.

The command uses the already-established:

`"spd": 0`
`"acc": 0`

No new velocity, acceleration, delta, workspace, or collision limit is
claimed by this milestone.

## Authorization

Each live joint motion requires:

1. State-aware validator ALLOW.
2. Connected/fresh controller state.
3. Local one-shot authorization.
4. Authorization age <= 120 seconds.
5. SHA-256 match of the authority implementation.
6. Shared exclusive motion lock.
7. Permit consumption before torque or motion.
8. Audit logging.

## Historical Documentation Status

Historical Session 28 and early Session 29 statements that describe the
ENTIRE RoArm MCP system as read-only are now superseded.

They remain historically accurate descriptions of the system at that time.

Current system state is:

- state/status tools: read-only
- proposal validators: dry-run, `hardware_action: NONE`
- `run_lissajous`: approved gated live motion
- `move_to_candle`: approved gated live motion
- `move_constrained_joint`: approved gated parameterized single-joint motion
- arbitrary joint motion: NOT authorized
- arbitrary Cartesian motion: NOT authorized
- unrestricted serial access: NOT exposed
- gripper control: NOT yet authorized as a separate live MCP capability

When historical session notes conflict with this current authority document
and the committed implementation, the current committed authority files
describe the active architecture.
