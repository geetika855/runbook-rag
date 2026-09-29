# New on-call: getting to understand the platform architecture

## Symptoms
- You're on-call (or newly joined) and don't have a mental model of the system.
- You can't answer: what runs where, what talks to what, and what breaks when
  something goes down.

## Likely causes (most common first)
1. No up-to-date architecture diagram exists.
2. Knowledge lives in people's heads and old Slack threads.
3. The platform grew organically — nobody designed the current state.

## Diagnosis steps — build the map yourself, in this order
1. **Namespaces:** `kubectl get namespaces` — each one is usually a team or
   environment boundary. Note which ones hold production workloads.
2. **Entry points:** `kubectl get ingress -A` (or Gateway API routes) — this
   is how traffic enters the cluster. Follow one route end to end.
3. **Workloads:** `kubectl get deployments,statefulsets -n <namespace>` —
   list what actually runs. For each: what does it do, who owns it?
4. **Data flow:** check ConfigMaps and Secrets mounts, then service-to-service
   calls — `kubectl get svc -n <namespace>` plus a look at the Grafana
   service graph / service mesh dashboard if one exists.
5. **State:** `kubectl get pvc -A` and managed datastores (RDS, ElastiCache,
   S3 buckets) — state is where the real risk lives.
6. **Pipelines:** find the CI/CD definitions (GitHub Actions workflows,
   ArgoCD applications) — `kubectl get applications -n argocd` shows what's
   GitOps-managed and which repo drives it.
7. **Observability:** open Grafana, find the "golden signals" dashboards
   (traffic, latency, errors, saturation) per service. Note which alerts page
   whom.

## Fix steps — turn the map into a shared artifact
1. Draw the architecture diagram (even a rough one) and store it in the repo
   or wiki — a bad diagram the team can correct beats no diagram.
2. Write the "if X goes down, Y breaks" dependency list next to it.
3. Add the three dashboards and five alerts that matter most to the on-call
   handover doc.

## Verify the fix
- You can whiteboard the request path from user → ingress → service →
  datastore without looking anything up.
- You know which dashboard to open for each of the top 3 incident types.

## Prevention / follow-up
- Make "update the architecture diagram" part of the definition of done for
  infra changes.
- Record a 15-minute architecture walkthrough video for the next new hire —
  future you will thank present you.
