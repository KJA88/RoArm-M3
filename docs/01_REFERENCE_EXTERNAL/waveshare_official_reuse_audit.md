# Official Waveshare Reuse Audit

Checked 2026-09-25 against current official sources. No hardware was moved. No production packet was changed.

This audit records what official Waveshare code could shorten, and what it must not replace. Physical evidence on this arm stays authoritative: HTTP live transport, T105 feedback over HTTP, no automatic motion retries, timeout after permit consumption is an uncertain outcome, one-shot motion authority, uninvolved joints preserved, READY as the default pre-pose.

Classes:

- A. Use directly.
- B. Adapt behind the safety and authority layer.
- C. Reference or validation only.
- D. Do not use.

No component is class A. Nothing below has been shown to match this arm and the production safety rules at the same time.

## Sources

| Source | Ref | Role |
| --- | --- | --- |
| [RoArm-M3-S Robotic Arm Control](https://www.waveshare.com/wiki/RoArm-M3-S_Robotic_Arm_Control) | oldid 109477 | Current M3 JSON motion semantics |
| [RoArm-M3-S JSON Command Meaning](https://www.waveshare.com/wiki/RoArm-M3-S_JSON_Command_Meaning) | oldid 109486 | HTTP, torque, dynamic adaptation, PID |
| [RoArm-M3-S Step Recording and Reproduction](https://www.waveshare.com/wiki/RoArm-M3-S_Step_Recording_and_Reproduction) | oldid 101875 | Mission record and playback |
| [RoArm-M3](https://www.waveshare.com/wiki/RoArm-M3) | product overview | spd 0 and acc 0 mean maximum |
| [waveshareteam/waveshare_roarm_sdk](https://github.com/waveshareteam/waveshare_roarm_sdk) | `d9893632aa7f5a9cb283136ab024faf3143ea7db` on `main`, 2026-08-12 | Current Python SDK |
| [waveshareteam/roarm_ws](https://github.com/waveshareteam/roarm_ws) | `fc2b0e40fab785f637dbd81918b79a0892c8f1f3` on `ros2-humble-develop-251125`, 2026-09-03 | Current ROS2 tree |
| [waveshareteam/roarm_ws](https://github.com/waveshareteam/roarm_ws) | `40dbd84b553695212fab713e8465f817ba95454d` on `ros2-humble`, 2025-07-25 | Default branch, older |
| [waveshareteam/roarm_m2](https://github.com/waveshareteam/roarm_m2) | `c6ccc5bda2eb92df2f0850d3e63cc42b81557f4f` on `main`, 2025-01-13 | M2 firmware header, protocol overlap only |
| [RoArm-M3 ROS2 Workspace Description](https://www.waveshare.com/wiki/RoArm-M3_ROS2_Workspace_Description) | oldid 101010 | Wiki ROS page; package list lags the develop branch |

The develop branch is the current ROS tree. It adds Gazebo, vision, and docs that the default `ros2-humble` branch and the wiki ROS page do not list. `roarm_ws_em0` is an older workspace and is not a source for this audit. No separate public M3 firmware repository was found. The M3 wiki says command numbers live in the product `json_cmd.h`. The published header in `roarm_m2` is the four-joint M2 command set. Use it for overlapping command numbers, and use the M3 wiki for M3 fields.

## T104 and T1041

Both commands are firmware inverse-kinematics goals for the end of the arm. The current control page, oldid 109477, distinguishes them as follows.

T104, `CMD_XYZT_GOAL_CTRL`, example `{"T":104,"x":235,"y":0,"z":234,"t":0,"r":0,"g":3.14,"spd":0.25}`:

- Includes `spd`. A larger value is faster.
- Curve speed control, so speed is not constant.
- No `acc` field.
- Blocks until the command finishes.

T1041, `CMD_XYZT_DIRECT_CTRL`, example `{"T":1041,"x":235,"y":0,"z":234,"t":0,"r":0,"g":3.14}`:

- No `spd` and no `acc`.
- No interpolation.
- Moves to the target at the fastest speed.
- Does not block.
- The JSON-command page, oldid 109486, describes it as a direct move that does not get stuck, and says it is suitable for a stream of new targets whose successive differences stay small.

T104 is the curve-speed, blocking goal command. T1041 is the direct, fastest, non-blocking goal command. The page does not give T1041 a smoother stop. It gives T1041 the fastest uninterpolated move. Neither command is a host trajectory. Both ask firmware IK for a pose.

The same JSON page documents HTTP as `GET http://<ip>/js?json=<command>` and prints `response.text`. That is the same channel production already uses. T1041 is therefore HTTP-addressable in the official demo. This arm has not executed T1041. Immediate HTTP bodies remain command acceptance, not settled pose.

Current SDK `roarm_sdk/common.py` sets `POSE_CTRL = 1041`. `handle_m3_pose` emits `x,y,z,t,r,g` and no speed. For `gripper_type="angular_direct"` it also replaces the gripper angle with `pi` minus that angle. Production T104 sends the raw T105 `r` and `g` radians and `spd` 0.5. The SDK pose path is a different command and a different gripper convention.

The step-recording page, oldid 101875, includes a sample mission step with T104 `spd` 0.5 as well as steps with `spd` 0.25. Production `spd` 0.5 matches one official mission example. The control-page example remains 0.25. Neither example is a measured gentle stop on this arm.

Production task-space probes stay on T104. The SDK `pose_ctrl` path stays off the production command path.

## HTTP feedback contradiction

Three official statements disagree.

The M3 JSON page says the HTTP demo returns feedback in the response body. This arm already reads T1051 over `http://192.168.4.1/js?json=...`.

Current SDK `roarm_sdk/roarm.py` at `d9893632` comments that HTTP is control-only, that firmware ACKs `{"ok":1}`, and that feedback requires serial. `_request_once` returns `None` for `FEEDBACK_GET` when `host` is set, and it discards the HTTP body for other commands.

M2 `http_server.h` at `c6ccc5b` writes `jsonInfoHttp` back on `/js`. That is M2 firmware, and it still returns a body.

Production keeps the HTTP reader. The SDK HTTP client is class D as a replacement.

## Geometry inside roarm_ws

File: `src/roarm_main/roarm_description/urdf/bases/roarm_m3.xacro` at `fc2b0e40`.

Revolute origins and limits, meters and radians:

| Joint | Origin xyz | Limit |
| --- | --- | --- |
| `base_link_to_link1` | 0.0100000008759151, 0, 0.0716 | ±3.1416 |
| `link1_to_link2` | 0, 0, 0.051959 | ±1.5708 |
| `link2_to_link3` | 0.236815, 0.030002, 0 | 0 to 2.95 |
| `link3_to_link4` | 0, −0.144586, 0 | ±1.5708 |
| `link4_to_link5` | 0.015147, −0.053653, 0 | ±3.1416 |
| `link5_to_gripper_link` | 0, 0.018821, 0.052035 | 0 to 1.5 |

`link5_to_hand_tcp` is fixed at `0, 0, 0.115428` m from `link5`. Collision geometry is the visual STL meshes scaled by 0.001. Frames are `world`, `base_link`, `link1` through `link5`, `gripper_link`, and `hand_tcp`.

The analytical model in `src/roarm_main/roarm_moveit_cmd/include/roarm_moveit_cmd/solver.hpp`, namespace `roarm_m3`, and the copy in `src/roarm_main/roarm_vision/roarm_vision/roarm_solver.py` uses millimeters:

- L1 126.06
- L2A 236.82, L2B 30.00
- L3A 144.49, L3B 0
- L4A 171.67, L4B 13.69

Those lengths are close to the URDF and not identical. The URDF shoulder-stack height is 71.6 + 51.959 = 123.559 mm, against solver L1 126.06 mm. URDF link2 is 236.815 by 30.002 mm, against 236.82 by 30.00. URDF link3 is 144.586 mm, against 144.49. The fixed `hand_tcp` offset 115.428 mm is a third tool length, distinct from L4.

The M3 control page states joint ranges that also differ from the URDF: elbow 0 to 3.14 rather than 0 to 2.95, and gripper 1.08 to 3.14 with a decrease opening the gripper, rather than URDF 0 to 1.5. Wiki initial elbow is 1.570796. Wiki gripper initial is 3.141593.

This repository’s fitted planar model uses shoulder-origin L1 about 238.839 mm and L2 about 316.731 mm. That L1 is near the official L2A, and that L2 is a fitted forearm, not official L3. The models answer different questions.

SRDF `config/roarm_m3/roarm_m3.srdf` names `ready` as base 0, shoulder 0, elbow 2.618, wrist −1.0472, roll 0. `initial_positions.yaml` uses that arm pose and gripper 0. Production READY is the verified arm-only target base 0.001533981, shoulder −0.832951568, elbow 2.399145952, wrist 0.004601942, with roll and gripper preserved. The official name `ready` is a different pose. Launching their MoveIt stack moves the arm to `initial_positions.yaml` as soon as the driver is running.

## Component classifications

| Component | Source file | Class | What it does | Help and concern | Verified here | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| M3 URDF, frames, meshes | `roarm_description/urdf/bases/roarm_m3.xacro` | C | CAD chain, joint origins, STL collision | Gives Milestone 08 a manufacturer geometry to compare. Limits and `hand_tcp` are unverified and disagree with the analytical tool length. | No | Offline numeric comparison with recorded T105. Do not command from it. |
| Analytical M3 FK and IK | `roarm_moveit_cmd/include/roarm_moveit_cmd/solver.hpp`; `roarm_vision/roarm_vision/roarm_solver.py` | B | Closed-form M3 FK and IK in millimeters | Can sit behind Milestone 09 as a predictor. Joint output must not be sent to hardware. Lengths disagree slightly with the URDF. | No | Compare predictions to stored T105 poses before any call site. |
| IKFast plugin | `roarm_moveit_ikfast_plugins/roarm_m3_hand_moveit_ikfast_plugin.xml`; `kinematics.yaml` | C | MoveIt IKFast61 plugin for group `hand`, tip `hand_tcp`, timeout 0.005 s | Faster host IK inside their MoveIt config. Tied to their frames and plugin API. | No | Leave it inside their tree. Use the plain solver for comparison. |
| MoveIt M3 config | `roarm_moveit/config/roarm_m3/` | C | SRDF groups, Pilz limits, controllers | Shows a host planning layout. `joint_limits.yaml` turns velocity and acceleration limits off. Default scaling 0.1 does not constrain those disabled limits. Named `ready` is not our READY. | No | Do not launch against this arm. |
| ros2_control | `roarm_m3.ros2_control.xacro`; `ros2_controllers.yaml` | D | Mock hardware on the real robot; Gazebo plugin only in simulation. `hand_controller` is a position trajectory controller at 100 Hz. | Their docs say the joint-state broadcaster publishes the mock state and the driver forwards it. Startup seeks `initial_positions.yaml`. | No | Keep it out of production. |
| Hardware driver | `roarm_driver/roarm_driver/roarm_driver.py` | D | Serial SDK client. Subscribes to `/joint_states` and sends `joints_radian_ctrl` at speed 1000, acc 50. | Every joint-state message can move the arm. Serial, continuous, no permit, no uncertain-outcome stop. Maps `base_link_to_link1` through `link5_to_gripper_link` onto the six radian fields. | No | Do not adopt the node. The joint-name list is reference only. |
| MoveIt Servo | `roarm_moveit_servo/config/roarm_config.yaml`; `src/keyboardcontrol.cpp` | D | Keyboard and joystick Cartesian jog through a vendored MoveIt Servo | Config still names group `arm` and topic `/panda_arm_controller/joint_trajectory`. Publishes trajectories at 100 Hz. Continuous streaming bypasses one-shot authority. | No | Do not use. |
| MoveIt Task Constructor | `roarm_moveit_mtc_demo/` plus vendored `src/roarm_else/moveit_task_constructor` | D | Pick-place demos, including AprilTag and YOLO variants | Execution goes through `move_group` and the serial driver. Their develop history includes a local MTC math patch. | No | Stage ideas stay reference. Do not vendor or execute. |
| Vision package | `roarm_vision/` | C for detectors; D for the pick path | USB camera, AprilTag, color, YOLOv8, then `/pick_place_cmd` trajectories | Perception code is a later reference for Phase 4. The hardware path publishes trajectories to the same driver. Camera origins in the xacro are mounts, not a calibration of this arm. | No | Keep our vision lessons. Do not connect their pick service. |
| SDK joint radian commands | `roarm_sdk/common.py` `handle_joint_radian_ctrl`, `handle_m3_joints_radian` | C | Passes T101 and T102 `spd` and `acc` through unchanged | Confirms the JSON fields. Does not define zero. Wiki semantics already recorded in Milestone 05 remain the behavior source. | Packet values are in production; this SDK file was not run | Leave packets unchanged. |
| SDK `pose_ctrl` | `roarm_sdk/common.py` `POSE_CTRL = 1041` | D | Emits T1041 and inverts `angular_direct` gripper | Replaces the verified T104 curve command with the fastest direct command and a different gripper angle. | No | Keep production on T104 with preserved raw `r` and `g`. |
| SDK HTTP client | `roarm_sdk/roarm.py` | D | Sends commands to `/js` and drops feedback in HTTP mode | Contradicts the M3 wiki HTTP demo and this arm’s T1051 reads. | Our HTTP reader is verified; this client is not | Keep `RoArmProductionHttpTransport`. |
| Gripper URDF and SRDF | xacro limit 0 to 1.5; SRDF `open` 1.5, `close` 0 | D | Model gripper range and named open/close | Contradicts the M3 wiki range 1.08 to 3.14 and our preset map 1.6, 2.0, 2.4, 2.8. Direction on the wiki matches our map: a smaller angle opens. The URDF numbers do not. | Our presets are the verified map | Keep `gripper_map.json`. |
| Mission record and playback | M3 wiki T220–T242, oldid 101875 | D | Flash missions, append current pose as T104, playback with `times`, including −1 for infinite | Useful description of manufacturer replay. Playback runs stored JSON on the ESP32, including loops, outside one-shot permits. | No | Do not call T242 or mission editors. |
| Dynamic adaptation | M3 wiki T112, oldid 109486; SDK `DYNAMIC_ADAPTATION_SET = 112` | D | Torque-limit mode that lets an external push move the arm and then rebound | Changes torque and can move the arm after release. The published example repeats the key `h` and the prose instead lists `g`. Servo torque limit also limits speed, by the page’s own note. | No | Do not send T112. |
| Torque switch | M3 wiki T210, oldid 109486 | C for the rule; D to send | cmd 0 unlocks, cmd 1 locks. A later rotation command turns torque back on. | Matches the existing rule that production does not automatically disable torque. | Torque behavior was not retested in this pass | Leave torque tri-state in the calibration tool. Do not add T210 to motion. |
| Joint PID | M3 wiki T108 and T109, oldid 109486 | C | P default 16, I default 0. The page says a high P oscillates and a high I jitters. | A manufacturer note relevant to post-stop rocking. It is not evidence that our rocking is PID. | No | Record only. Do not retune. |
| M2 firmware header | `roarm_m2` `RoArm-M2_example/json_cmd.h` | C | M2 command numbers, including T104 and T1041 | M2 T102 example has no wrist or roll. M2 comments call T101 acc `steps/s^2`. The M3 wiki unit is 100 steps/s^2. Prefer the M3 page for this arm. | No | Use only where the M3 wiki names the same command. |

## What this changes on the roadmap

Host geometry and the plain M3 analytical solver can shorten Milestone 08 and Milestone 09 by giving an official model to compare with recorded T105. That comparison is offline. It does not become the commander.

MoveIt, Servo, Task Constructor, the serial driver, and the vision pick path all end in continuous or startup motion over serial. They do not replace HTTP, one-shot permits, or READY. Integrating them would lengthen the safety problem rather than shorten the roadmap.

Production T104 with `spd` 0.5 remains the verified task-space command. Official current documentation describes that command as blocking curve-speed IK, and describes the SDK’s T1041 as the fastest uninterpolated goal.
