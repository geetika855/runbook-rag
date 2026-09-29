# EKS: no IP address available for new pods

## Symptoms
- New pods stuck in `Pending` during or right after a deploy/scale-up.
- `kubectl describe pod` shows: `failed to assign an IP address to container`.
- The `aws-node` (VPC CNI) logs show `no available IP addresses` or
  `Insufficient free addresses`.

## Likely causes (most common first)
1. **Subnet IP exhaustion** — the EKS VPC CNI assigns real VPC IPs to pods
   from the node's subnets. When the subnets run out of free IPs, no new pod
   can start. Most common after traffic-driven scale-ups.
2. **Prefix delegation disabled** — without it, each ENI gets few IPs, so
   nodes hit their pod limit long before the subnet is full.
3. **Leaked ENIs** — stale elastic network interfaces from deleted nodes hold
   IPs hostage.
4. **maxPods too low** for the instance type (kubelet cap, not IP-related but
   looks identical: pods stay Pending).

## Diagnosis steps
1. Confirm the symptom: `kubectl describe pod <pod> -n <namespace>` — look
   for `failed to assign an IP address` in Events.
2. Check CNI logs: `kubectl logs -n kube-system -l k8s-app=aws-node | grep -i "no available ip"`.
3. Check subnet free IPs: `aws ec2 describe-subnets --subnet-ids <ids>
   --query 'Subnets[*].AvailableIpAddressCount'`.
4. Check whether prefix delegation is on:
   `kubectl get daemonset aws-node -n kube-system -o jsonpath='{.spec.template.spec.containers[0].env}' | grep -i prefix`.

## Fix steps
1. **Immediate relief:** enable prefix delegation — each ENI then gets a /28
   prefix (16 IPs) instead of individual IPs, massively raising per-node pod
   capacity:
   `kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true`
   (then restart the aws-node pods).
2. **If subnets are truly full:** add a secondary CIDR block to the VPC and
   add new subnets, then add them to the cluster's subnet tags so new nodes
   launch there.
3. Clean up leaked ENIs in the EC2 console (filter by the cluster tag,
   delete ones not attached to live instances).
4. If it's the kubelet maxPods cap instead: raise `--max-pods` via the node
   group's kubelet config or user data.

## Verify the fix
- Pending pods transition to `Running` and receive IPs.
- `AvailableIpAddressCount` on subnets stops dropping; CNI logs go quiet.

## Prevention / follow-up
- Enable prefix delegation from day one on every EKS cluster.
- Alert on subnet IP utilization (e.g. < 20% free IPs) — don't discover this
  during a deploy.
- Size subnets generously; a /24 per AZ disappears fast with pod-level IPs.
- Consider VPC CNI custom networking for large clusters.
