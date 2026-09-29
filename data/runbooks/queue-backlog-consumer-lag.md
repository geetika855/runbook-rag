# Queue backlog and consumer lag

## Symptoms
- Queue depth (messages waiting) keeps growing; consumers can't keep up.
- Alert on consumer lag or `ApproximateAgeOfOldestMessage` (SQS) / consumer
  lag in messages or seconds (Kafka).
- Downstream effects: delayed notifications, stale data, SLA breaches.

## Likely causes (most common first)
1. **Traffic spike** — producers suddenly emitting faster than consumers drain.
2. **Slow consumer** — a downstream dependency (DB, API, model endpoint) got
   slower, so each message takes longer to process.
3. **Poison message** — one malformed message crashes or stalls the consumer
   on every retry, blocking everything behind it.
4. **Consumer outage or rebalance storm** — consumers crashed, or Kafka
   rebalance keeps reassigning partitions so nobody makes progress.
5. **Under-provisioned consumers** — too few replicas / too little
   concurrency for the steady-state load.

## Diagnosis steps
1. Check the shape of the problem: is depth growing linearly (too slow) or
   did it spike vertically (outage then recovery)? Grafana queue-depth graph.
2. Check consumer health: `kubectl get pods -n <namespace>` for the consumer
   deployment — crashing? OOMKilled?
3. Check consumer logs for repeated errors on the same message ID — the
   poison-message signature.
4. Check downstream latency: if the consumer calls a DB/API, its p99 latency
   graph usually explains the slowdown.
5. For Kafka: `kafka-consumer-groups --describe` — which partitions lag, and
   is the lag concentrated (one slow partition) or everywhere?

## Fix steps
1. Poison message: let it exhaust retries into the **dead-letter queue**, or
   manually skip it; fix the consumer to handle that payload shape.
2. Slow downstream: scale or fix the downstream first — adding consumers
   against a saturated DB just moves the queue.
3. Under-provisioned: scale consumers —
   `kubectl scale deployment <consumer> -n <namespace> --replicas=<n>` —
   and raise per-pod concurrency if the consumer supports it.
4. Traffic spike: temporarily scale up, then decide if the new level is the
   new normal (resize permanently).
5. Rebalance storm: check for crashing consumers causing the rebalance loop;
   fix the crash, not the rebalance.

## Verify the fix
- Queue depth and age-of-oldest-message trending down to baseline.
- Consumer lag near zero across all partitions.
- No new poison messages landing in the DLQ.

## Prevention / follow-up
- **Always** configure a DLQ with a redrive policy — poison messages should
  never block a queue.
- Autoscale consumers on backlog depth, not just CPU.
- Alert on *age of oldest message*, not just depth — 10 old messages are
  worse than 10,000 fresh ones.
- Load-test consumers against realistic downstream latency, not just
  message volume.
