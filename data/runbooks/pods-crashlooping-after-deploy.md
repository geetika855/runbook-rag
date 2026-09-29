# Pods crashlooping after deploy

## Symptoms
- Alert `KubePodCrashLooping` fires for the newly deployed pods.
- `kubectl get pods -n <namespace>` shows `CrashLoopBackOff` with rising restart counts.

## Likely causes (most common first)
1. Bad container image (broken build or wrong tag pushed).
2. Missing or misnamed environment variable / secret.
3. Failed init dependency (e.g. model artifact not downloadable at startup).

## Diagnosis steps
1. Read the crash logs: `kubectl logs <pod> -n <namespace> --previous`.
2. Describe the pod for events: `kubectl describe pod <pod> -n <namespace>`.
3. Check the image actually exists: compare `kubectl get deployment <name>
   -o jsonpath='{.spec.template.spec.containers[0].image}'` against the registry.

## Fix steps
1. If bad image: roll back immediately —
   `kubectl rollout undo deployment/<name> -n <namespace>`.
2. If missing env/secret: fix the manifest or secret, then
   `kubectl rollout restart deployment/<name> -n <namespace>`.
3. If init dependency: check artifact bucket permissions, then restart.

## Verify the fix
- All pods `Running` and `READY 1/1`, restart count stops increasing.
- Readiness probe passing for 5 minutes.

## Prevention / follow-up
- Add a smoke-test step in CI that boots the image and hits `/healthz`.
- Require image digest pins (not `:latest`) in production manifests.
