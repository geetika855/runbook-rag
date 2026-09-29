# Runbook template

Copy this file for each incident type. Write it the way you'd explain the fix
to a teammate at 2 AM: concrete commands, dashboards, and what "fixed" looks
like. Keep names generic — no company or cluster secrets.

## Title
<e.g. Inference API latency spike>

## Symptoms
- What alerts fire? (e.g. `InferenceLatencyP99 > 800ms for 5m`)
- What does the user/team notice?

## Likely causes (most common first)
1.
2.

## Diagnosis steps
1. <exact command or dashboard link, e.g. `kubectl top pods -n inference`>
2.

## Fix steps
1.
2.

## Verify the fix
- <e.g. p99 latency back under 300ms for 10 minutes, error rate < 0.1%>

## Prevention / follow-up
- <e.g. tune Karpenter consolidation, add alert on queue depth>
