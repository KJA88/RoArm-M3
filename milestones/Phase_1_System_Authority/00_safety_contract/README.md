# Milestone 00: Safety Contract
This milestone establishes the "Safe Boot" protocol for the RoArm-M3.

## Implementation
The safety logic is integrated into the core `RoArmSupervisor` class. 
- **Torque Management:** The system ensures torque is explicitly managed during startup to prevent the arm from collapsing or "jumping" due to residual capacitor charge.
- **Zero-Energy State:** Procedures are established to return the arm to a stable physical state before software shutdown.
