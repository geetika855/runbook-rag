# Kubernetes pod is not running

## Symptoms
- `kubectl get pods -n <namespace>` shows the pod stuck in `Pending`,
  `ContainerCreating`, `ImagePullBackOff`, or `CrashLoopBackOff` instead of `Running`.
- Alert `KubePodNotReady` fires; the owning deployment never becomes available.

## Likely causes (most common first)
1. **Pending:** no node with enough CPU/memory, node affinity or taints
   excluding all nodes, or a PersistentVolumeClaim that can't bind.
2. **ImagePullBackOff:** wrong image tag, missing imagePullSecret, or registry
   unreachable.
3. **CrashLoopBackOff:** app crashing on start (bad config, missing env var or
   secret, failing dependency).

## Diagnosis steps
1. Get the overview: `kubectl get pods -n <namespace> -o wide`.
2. Read the scheduler/app events: `kubectl describe pod <pod> -n <namespace>`
   — the Events section usually names the cause directly.
3. For Pending: `kubectl get nodes` and `kubectl top nodes` to check capacity;
   `kubectl get pvc -n <namespace>` to check volume binding.
4. For ImagePullBackOff: verify the image exists in the registry and the
   imagePullSecret is present: `kubectl get secret <secret> -n <namespace>`.
5. For CrashLoopBackOff: `kubectl logs <pod> -n <namespace> --previous`.

## Fix steps
1. Pending on capacity: scale the node pool or lower the pod's resource
   requests if they're over-provisioned.
2. Pending on affinity/taints: fix the nodeSelector/affinity in the manifest,
   or add the matching toleration.
3. PVC won't bind: check the StorageClass exists and the provisioner is
   healthy; delete a stuck PVC only if its data is disposable.
4. ImagePullBackOff: correct the tag, create the imagePullSecret
   (`kubectl create secret docker-registry ...`), or fix registry credentials.
5. CrashLoopBackOff: fix the underlying app config/secret, then
   `kubectl rollout restart deployment/<name> -n <namespace>`.

## Verify the fix
- Pod shows `Running` with `READY 1/1` (or `n/n`).
- `kubectl get events -n <namespace>` shows no new warnings for the pod.

## Prevention / follow-up
- Set sane CPU/memory requests AND limits on every workload.
- Pin image digests; never deploy `:latest` to production.
- Keep imagePullSecrets in place via the namespace's default service account.
