# Discovery: mapping the existing process (deploys, releases, incidents)

## Symptoms
- Nobody can say exactly how a deploy, release, or incident response
  *actually* happens today — only how it's *supposed* to happen.
- Docs describe a process the team stopped following months ago.

## Likely causes (most common first)
1. The process evolved through incidents and shortcuts; docs didn't follow.
2. Different teams follow different variants of the "same" process.
3. Tribal knowledge: one or two people hold the real procedure in their heads.

## Diagnosis steps — trace the process from its artifacts, not from memory
1. **Deployments:** find the CI/CD definitions first — `.github/workflows/`,
   ArgoCD `Application` manifests (`kubectl get applications -n argocd`),
   Jenkinsfiles. The pipeline config IS the current deploy process.
2. **Releases:** check git tags, release branches, and changelogs. Then ask:
   who decides what ships, and where is that decision recorded (a Slack
   channel? a ticket? someone's head?).
3. **Incidents:** read the last 3 incident tickets/post-mortems end to end.
   Note the actual sequence: who got paged, what they tried first, how long
   each step took. Reality lives here.
4. **Access & approvals:** list who can deploy to prod and what (if anything)
   gates it — a manual approval step, a code owner review, nothing at all?
5. **Shadow steps:** ask each person involved "what do you do that isn't
   written down?" — the manual kubectl commands, the Slack DM approvals,
   the "oh I always check that dashboard first."

## Fix steps — write down what you found, then improve it
1. Document the **as-is** process exactly as traced — resist the urge to
   write the ideal version. Label every shadow step honestly.
2. Get the people who live it to review and correct it (they will).
3. Only then propose the **to-be**: automate the most painful manual step
   first, not the whole process at once.

## Verify the fix
- A new team member can follow the written process for a deploy without
  asking anyone a question.
- The next incident's timeline matches the documented response process.

## Prevention / follow-up
- Review the process doc after every incident — post-mortems are where
  processes actually change.
- If a step is always skipped, delete it from the doc instead of pretending.
