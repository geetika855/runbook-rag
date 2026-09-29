# Inference API latency spike

## Symptoms
- Alert `InferenceLatencyP99` fires: p99 latency above 800ms for 5 minutes.
- Users report slow responses from the inference endpoint.

## Likely causes (most common first)
1. Traffic spike outpacing current replica count (autoscaler lag).
2. A new model version with higher per-request compute cost.
3. Noisy neighbor / node CPU pressure in the inference node pool.

## Diagnosis steps
1. Check current load vs capacity: `kubectl top pods -n inference` and compare
   request rate on the Grafana "Inference Traffic" dashboard.
2. Check Karpenter events: `kubectl get events -n inference --sort-by=.lastTimestamp`
   — look for pending pods or consolidation churn.
3. Compare latency by model version label in Grafana; a step-change at a deploy
   boundary points at the new model.

## Fix steps
1. If traffic-driven: temporarily raise min replicas —
   `kubectl scale deployment inference-api -n inference --replicas=<2x current>`.
2. If model-driven: roll back — `kubectl rollout undo deployment/inference-api -n inference`.
3. If node pressure: cordon the hot node and let Karpenter reprovision —
   `kubectl cordon <node>` then verify new nodes join.

## Verify the fix
- p99 latency back under 300ms sustained for 10 minutes.
- Error rate under 0.1% and no pending pods.

## Prevention / follow-up
- Add a queue-depth / pending-pod alert that fires before latency degrades.
- Review Karpenter consolidation settings so scale-up reacts faster to bursts.
