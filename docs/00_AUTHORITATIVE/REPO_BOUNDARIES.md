# Repository Boundaries

## Executable Zones
Code is allowed to run ONLY from:
- lessons/
- milestones/
- roarm_simple_move.py
- roarm_ws/

## Frozen Zones (Do Not Execute)
- archive/
- _archive/
- _clutter_backup/

These folders are historical and must not be imported or executed.

## Control Layers
- SDK control → lessons/, milestones/
- Raw UART → experiments only
- Legacy hybrids → archive (frozen)
