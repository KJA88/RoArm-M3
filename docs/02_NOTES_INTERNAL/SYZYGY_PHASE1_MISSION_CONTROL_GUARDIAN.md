# SYZYGY Phase 1 — Mission Control + Guardian

Status: ACTIVE PLANNING / READ-ONLY IMPLEMENTATION
Branch: `syzygy-phase1-mission-control`
Owner: KJA
Operators: ChatGPT + Grok

## Purpose

Turn the existing SYZYGY collection of devices, MCP services, dashboards, tunnels, and AI clients into one observable system.

Phase 1 is deliberately read-only with respect to robot motion. It must not issue RoArm joint or task-space commands.

## Non-negotiable safety boundary

The existing RoArm authority model remains unchanged:

- no direct vision-to-motion control
- no raw UART control for production behavior
- no arbitrary shell/filesystem control exposed through Mission Control
- no robot motion from Guardian health checks
- motion-capable work remains governed by the existing milestones and deterministic command/response rules

Guardian may observe robot state only through already-approved read/state interfaces.

## Phase 1A — Mission Control dashboard

First useful dashboard slice should expose:

1. Pi health
   - online/offline
   - CPU load
   - memory
   - disk
   - temperature where available
   - uptime

2. Jetson health
   - online/offline
   - CPU/GPU load where available
   - memory
   - disk
   - temperature
   - uptime

3. MCP service inventory
   - server name
   - local endpoint status
   - public endpoint status
   - tool count
   - last successful probe
   - last failure
   - latency

4. Cloud/public path health
   - DNS/TLS/public endpoint reachability
   - MCP HTTP response health
   - distinguish endpoint/network failure from client-auth/session failure

5. AI/client path status
   - portal/catalog visible
   - last successful real tool invocation when measurable
   - auth/session stale vs server unavailable

6. Recent events
   - timestamp
   - trace ID
   - component
   - severity
   - event summary

7. Global status
   - GREEN: all required components healthy
   - YELLOW: degraded but usable
   - RED: required path broken

## Phase 1B — Guardian

Guardian is a deterministic probe pipeline, not an autonomous repair daemon yet.

Probe chain for each service:

`host -> local service -> local MCP -> public hostname -> portal/catalog -> real harmless tool call`

The pipeline must record exactly where the failure occurs.

Example result:

```text
service: tv-mcp
trace_id: syz-20260923-000123
host: PASS
local_service: PASS
local_mcp: PASS
public_tls: PASS
public_mcp: PASS
portal_catalog: PASS
client_invoke: FAIL
classification: STALE_CLIENT_AUTH_OR_SESSION
```

## Trace IDs

Every Guardian run should create a trace ID and pass/log it wherever practical.

Suggested format:

`syz-YYYYMMDD-HHMMSS-xxxx`

The objective is to correlate one user-visible failure across Pi/Jetson/service/tunnel/portal/client logs.

## Data model — initial proposal

```json
{
  "timestamp": "ISO-8601",
  "trace_id": "syz-...",
  "system": {
    "status": "green|yellow|red"
  },
  "nodes": {
    "pi": {},
    "jetson": {}
  },
  "services": [
    {
      "name": "tv-mcp",
      "host": "pi",
      "local_ok": true,
      "public_ok": true,
      "tool_count": null,
      "latency_ms": null,
      "last_ok": null,
      "last_error": null
    }
  ],
  "events": []
}
```

## Initial known SYZYGY service/path examples

These are inputs to verify against the live deployment before treating them as authoritative:

- unified MCP entry point: `https://mcp.syzygylab.net/mcp`
- Pi Git Audit MCP: `https://pi-git.syzygylab.net/mcp`
- Jetson Git Audit MCP: `https://jetson-git.syzygylab.net/mcp`
- TV MCP public path: `https://tv.syzygylab.net/mcp`
- TV MCP local service observed previously at `127.0.0.1:8065/mcp`
- Pi kiosk/dashboard observed previously at `http://192.168.1.17:8080/`

All endpoint values above must be discovered/verified from current deployment state before code depends on them.

## Grok assignment

Grok is the parallel architecture/reliability reviewer for Phase 1.

### Task G1 — Architecture critique

Review this Phase 1 design and identify:

- hidden single points of failure
- health checks that could report false green
- missing observability layers
- unsafe coupling between dashboard/Guardian and motion-capable code
- how to separate infrastructure state from robot state

Return concrete changes only; avoid wholesale redesign unless required.

### Task G2 — Failure taxonomy

Create a failure classification table covering at least:

- host offline
- service stopped
- port unavailable
- MCP protocol failure
- tunnel down
- DNS failure
- TLS failure
- Cloudflare/portal routing failure
- stale OAuth/session
- tool catalog stale
- tool invocation failure
- timeout
- partial dependency outage

For each: observable symptoms, best probe, classification code, recommended human action.

### Task G3 — Test cases

Generate deterministic tests for Guardian that can be executed without moving the robot.

At minimum include:

- all-green path
- local service down
- public path down while local path is healthy
- stale client auth/session while server remains healthy
- timeout
- malformed MCP response
- dependency unavailable
- recovery on next probe

## ChatGPT assignment

ChatGPT owns implementation coordination for Phase 1:

1. inventory the current repo and deployed services
2. identify the existing dashboard app/service
3. define the Guardian probe schema
4. implement read-only probes first
5. surface results in the dashboard
6. add trace correlation and event history
7. document deployment/runbook changes
8. verify using harmless real calls only

## Definition of Done — Phase 1 first slice

A first slice is complete when one screen can truthfully show:

- Pi health
- Jetson health
- at least three MCP service statuses
- local-vs-public path distinction
- last probe timestamp
- last failure reason
- one trace ID linking a Guardian run

and when a deliberately stopped non-motion service causes the dashboard to move from green to degraded/red with the correct failure layer identified.

## Next implementation step

Locate the existing SYZYGY dashboard source/service and the currently deployed MCP service definitions. Do not create a second dashboard until the existing one is understood.
