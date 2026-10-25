# ECR-5G backend

ECR-5G (Evidence-Completeness-Constrained QoS) is a deterministic, CPU-only emulator for comparing packet scheduling policies during emergency communications. It is not a 5G network controller, a 3GPP conformance test, or an operational safety certification. The included scenario data is synthetic. It cannot configure a network or authorize an action.

## Controllers and evidence gate

- `FIFO_BASELINE` selects the oldest ready packet.
- `STATIC_QOS_BASELINE` selects by fixed emergency, critical, standard, then bulk class, with deadline and arrival tie-breaks.
- `ECAC_CONTROLLER` reevaluates ready per-flow queue heads on each transmission. Eligible mandatory evidence is ordered by earliest requirement deadline, freshness slack, number of dependent requirements, payload size, then stable arrival/sequence identifiers. It will not let optional traffic displace eligible mandatory evidence while the configured mandatory-preemption rule applies. A configured maximum mandatory burst prevents indefinite optional-flow starvation. Promotion only changes emulator scheduling; it never changes live QoS.

For each mandatory action requirement, completeness requires matching incident, evidence type, requirement reference, permitted source, freshness, verification and integrity status, no unresolved conflict, and successful packet delivery before that requirement's deadline. Missing or stale evidence never passes because a packet was sent. Completed evidence gates return `READY_FOR_HUMAN_REVIEW` when approval is required; every result keeps `authorized: false`.

All strategies receive the same per-flow message queues, generated trace, event windows, and seed. Per-message random loss is derived from the seed and stable message identity. The simulator processes time events without sleeping. Serialization carries remaining bits across capacity changes and pauses during outages, then resumes at recovery. Propagation and configurable processing delays are applied after serialization. It does not emulate radio, core, handover, retransmission, or standards-level protocol details.

The ready-queue policy selects the best packet by scanning the bounded ready set; pending arrivals are kept in deterministic arrival order. For `P` generated packets the simple scheduler is `O(P²)` worst case and uses `O(P)` memory. The fixed catalogue has bounded duration and generated traffic; this implementation prioritizes an auditable reference emulator over high-throughput simulation.

## API

All endpoints require the existing NetraSetu session. POST requests also require the existing `X-CSRF-Token` header.

| Method and route | Purpose |
| --- | --- |
| `GET /api/ecr5g/health` | Simulation service status |
| `GET /api/ecr5g/scenarios` | Eight synthetic scenario fixtures |
| `GET /api/ecr5g/scenarios/{scenario_id}` | Scenario details |
| `POST /api/ecr5g/simulations/run` | Run one scenario against one or more controllers |
| `GET /api/ecr5g/simulations/{run_id}` | Retrieve the persisted run envelope |
| `GET /api/ecr5g/simulations/{run_id}/report` | Retrieve the persisted comparison report |

Run request example:

```json
{
  "scenario_id": "HG-ECAC-001",
  "strategies": ["FIFO_BASELINE", "STATIC_QOS_BASELINE", "ECAC_CONTROLLER"],
  "seed": 17
}
```

Run reports are stored as `ECR5G_SIMULATION` records using NetraSetu's existing audit JSONL writer. No separate audit database or frontend is introduced.

## Metrics and interpretation

- Latency reports mean, p50, p95, p99 and maximum effective latency. Undelivered packets use a documented 60,000 ms penalty in effective summaries; `delivered_only_mean` is reported separately.
- Latency percentiles are over all generated messages, using end-to-end arrival-to-delivery milliseconds; undelivered messages receive the 60,000 ms penalty. Delivered-only and network-only means are separate fields.
- Jitter is the mean absolute latency difference between consecutive messages in each flow. Undelivered messages use the same penalty.
- Message loss rate = all undelivered messages / all generated messages. Random loss draws are broken out separately; outage or horizon failures still count as loss.
- Deadline success = messages delivered by each flow deadline / all generated messages. The report lists each failed message and reason.
- Evidence completeness = satisfied mandatory action/requirement pairs / all mandatory pairs. The report also provides per-requirement deadlines, reason codes, stale evidence rejected, and unresolved conflict counts.
- Bytes transmitted include partial messages. Bottleneck utilization = serialized bytes / the integrated available capacity budget in bytes, capped at 1.0.
- Queueing delay is arrival-to-first-bit time, including outage wait; mean, maximum, and maximum simultaneously queued messages are reported.
- Controller computation time accumulates packet-selection wall time. Evidence validation time is measured separately. API request latency is `null` in simulator output and must be measured at an HTTP client boundary.
- `scheduler_priority_promotions` counts selected ECAC messages whose evidence rule improved scheduler rank. `live_qos_policy_changes` is always zero.
- Infeasible schedules include explicit unmet action requirement IDs and reasons. The simulator reports a count of failed safety invariant checks; any nonzero count is a run defect, not an operational result.

## Run and verify on Windows

From the repository root, with the project's Python environment active:

```powershell
python -m pytest Backend/tests/test_ecr5g.py -q
```

For more credible radio/access-network evaluation, export the same trace and compare in a calibrated ns-3 or 5G-SA testbed. Keep evidence adjudication and human authorization as separate stages; never treat a simulation result as an operational instruction.
