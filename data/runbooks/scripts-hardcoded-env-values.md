# Scripts with hardcoded environment and account details

## Symptoms
- A deploy or ops script works in dev but breaks in staging/prod.
- Account IDs, region names, bucket names, or cluster names are written
  directly into shell/Python scripts.
- Secrets or access keys appear in script files or shell history.
- Nobody dares to run the script against a new environment.

## Likely causes (most common first)
1. The script was written for one environment and copy-pasted for others.
2. No convention for passing environment context (env vars, flags, config).
3. Credentials baked into the script instead of pulled from a secret store
   or IAM role.

## Diagnosis steps
1. Find the hardcoding: `grep -rnE '[0-9]{12}' scripts/` (AWS account IDs),
   `grep -rniE 'us-east-1|prod|staging' scripts/` — every hit is a candidate.
2. Classify each hit: is it a **target** (account, region, cluster, bucket) or
   a **secret** (key, token, password)? They get fixed differently.
3. Check how the script is invoked — does CI pass anything in, or does it
   assume it's running somewhere specific?

## Fix steps
1. **Targets → variables.** Replace literals with env vars or flags, with
   safe defaults:
   ```bash
   AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?must be set}"
   AWS_REGION="${AWS_REGION:-us-west-2}"
   CLUSTER="${CLUSTER:?must be set}"
   ```
   The `:?` form fails fast with a clear message instead of silently doing
   the wrong thing in the wrong account.
2. **One script, many environments.** Drive differences from a small config
   file per environment (`envs/dev.env`, `envs/prod.env`), never from
   `script-dev.sh` / `script-prod.sh` copies.
3. **Secrets → never in the script.** Pull from the environment, AWS Secrets
   Manager / Parameter Store, or an IAM role. `set -x` tracing must never
   print them — use `set +x` around sensitive sections.
4. **Account safety guard.** At the top of any mutating script, assert you're
   in the right account:
   ```bash
   actual=$(aws sts get-caller-identity --query Account --output text)
   [ "$actual" = "$AWS_ACCOUNT_ID" ] || { echo "wrong account: $actual"; exit 1; }
   ```
   This one check prevents the classic "ran the prod script in dev" disaster
   — in both directions.

## Verify the fix
- `grep` for the old literals returns nothing.
- The script runs unchanged in two different environments with only env
   vars differing.
- A dry-run / plan mode shows the target account before anything mutates.

## Prevention / follow-up
- Add a CI check that greps scripts for 12-digit account IDs and known
  secret patterns (or use gitleaks).
- Template new scripts from one parameterized skeleton.
- Document required env vars at the top of every script.
