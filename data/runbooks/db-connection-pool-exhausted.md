# Database connection pool exhausted

## Symptoms
- App logs fill with `too many connections`, `connection pool exhausted`, or
  timeouts waiting for a connection from the pool.
- Latency spikes and failed health checks, often right after a deploy that
  increased replica count or traffic.
- The database itself looks fine on CPU — it's the connection count that's
  pegged at max.

## Likely causes (most common first)
1. **Connection leak** — code opens connections and never returns them to
   the pool (missing close in an error path is the classic).
2. **Pool too small for the load** — traffic grew, pool size didn't.
3. **Replicas × pool size explosion** — 20 app pods × 50 pooled connections
   each = 1000 connections against a DB max of 500.
4. **Idle-in-transaction** — connections held open by unfinished
   transactions, often from a long-running query or a forgotten commit.
5. **No pooler** — every app pod connects directly to the DB instead of
   going through PgBouncer/RDS Proxy.

## Diagnosis steps
1. Check the numbers: current connections vs max —
   `SELECT count(*) FROM pg_stat_activity;` vs `SHOW max_connections;`
   (Postgres) or the `DatabaseConnections` CloudWatch metric (RDS).
2. Find who's holding them:
   `SELECT application_name, state, count(*) FROM pg_stat_activity GROUP BY 1,2;`
   — a pile of `idle in transaction` is the smoking gun.
3. Correlate with deploys: did connection count step up exactly when the new
   version rolled out? Check the pool-size env var in the new manifest.
4. Check for leaks: connections climbing steadily with flat traffic means
   something isn't closing them.

## Fix steps
1. **Immediate relief:** terminate the idle offenders —
   `SELECT pg_terminate_backend(pid) FROM pg_stat_activity
    WHERE state = 'idle in transaction' AND state_change < now() - interval '5 minutes';`
   (careful: this kills real work too — prefer it in a crisis, then fix the cause).
2. Fix the leak in code (unclosed connections in error paths), or roll back
   the deploy that introduced it.
3. Right-size pools: total connections ≈ (pods × pool_size) must stay well
   under DB max. Shrink per-pod pools before adding pods.
4. **Put a pooler in front** — PgBouncer in transaction-pooling mode (or RDS
   Proxy). This is the real fix for the replicas × pool-size explosion: 1000
   app-side connections multiplex into ~50 real DB connections.
5. Set `statement_timeout` and `idle_in_transaction_session_timeout` so one
   bad query can't hold connections hostage.

## Verify the fix
- Connection count back near baseline and stable under load.
- No more pool-exhaustion errors in app logs for a full traffic cycle.
- p99 latency recovered.

## Prevention / follow-up
- Never let app pods connect directly to production DBs — pooler is
  mandatory, not optional.
- Alert on connection utilization (> 70% of max), not just on exhaustion.
- Load-test with realistic replica counts — pool math must include the
  autoscaler's max, not just today's replica count.
- Review pool-size settings in every deploy diff, like you'd review
  resource limits.
