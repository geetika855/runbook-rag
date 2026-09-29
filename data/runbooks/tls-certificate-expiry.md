# TLS certificate expiry

## Symptoms
- Browsers show `NET::ERR_CERT_DATE_INVALID`; `curl` fails with
  `certificate has expired`.
- External traffic to the ingress/API stops working while everything looks
  healthy inside the cluster.
- Alerts from cert-manager (`CertificateExpiration`) or an SSL exporter fire
  — or worse, nothing fired and users found it first.

## Likely causes (most common first)
1. **Auto-renewal failed silently** — cert-manager couldn't complete the
   ACME challenge (HTTP-01 or DNS-01) and the old cert aged out.
2. **Manually-provisioned cert** that someone forgot to rotate.
3. cert-manager itself was down or its ClusterIssuer misconfigured, so no
   renewals were even attempted.
4. ACME **rate limits** hit after repeated failed issuances.

## Diagnosis steps
1. Check the actual expiry from outside:
   `echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates`
2. Check cert-manager's view: `kubectl get certificate -A` and
   `kubectl describe certificate <name> -n <namespace>` — look at
   `Not After` and the Status conditions.
3. Check for stuck challenges/orders:
   `kubectl get challenges,orders -A` — a pending Challenge with errors
   points at the ACME solver (DNS record missing? ingress unreachable?).
4. Check cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`.

## Fix steps
1. Fix the underlying challenge issue first (DNS record, ingress
   reachability, credentials for DNS-01 solver).
2. Force an immediate renewal: `cmctl renew <certificate> -n <namespace>`
   (or delete the stale `Order`/`Challenge` resources and let cert-manager
   recreate them).
3. For a manual cert: generate/obtain the new cert, update the TLS Secret,
   and restart or reload the ingress controller.
4. If rate-limited by Let's Encrypt: wait out the limit, or temporarily use
   the staging issuer / a backup CA.

## Verify the fix
- `openssl s_client` shows a fresh `Not After` date far in the future.
- `kubectl describe certificate` shows `Ready: True`.
- External `curl https://<host>` succeeds with no warnings.

## Prevention / follow-up
- Alert on cert expiry at **30, 14, and 7 days** — never rely on a single
  threshold.
- Prefer cert-manager over manual certs everywhere; manual certs are
  incidents waiting for a calendar reminder.
- Add an external blackbox check (e.g. Prometheus blackbox exporter on
  `probe_ssl_earliest_cert_expiry`) — in-cluster views can lie if
  cert-manager itself is the problem.
