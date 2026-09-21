# Protecting `main`

The rule for this repository is: **nothing reaches `main` except through a
pull request whose `validate` check has passed.**

This is enforced server-side by the `protect-main` ruleset, which is active.
Read back exactly what applies at any time with:

```bash
gh api repos/einot/agent-kit-skills/rules/branches/main
```

## What the ruleset enforces

| Rule | Effect |
| --- | --- |
| `pull_request` | No direct pushes to `main`; merges go through a PR |
| `required_status_checks` | `validate` must pass, and the branch must be up to date with `main` (`strict`) |
| `non_fast_forward` | Force-pushes to `main` are refused |
| `deletion` | `main` cannot be deleted |

`required_approving_review_count` is **0**, because a solo maintainer cannot
approve their own pull request — a count of 1 would lock you out of your own
repository. Raise it to 1 as soon as there is a second maintainer:

```bash
gh api -X PUT repos/einot/agent-kit-skills/rulesets/23732658 --input .github/ruleset-main.json
```

(after editing the count in that file).

GitHub also applies `require_extra_approval_for_unattributed_changes`, which
demands an extra approval for commits whose author email is not linked to a
GitHub account. Keep committing with an email attached to your account —
otherwise, as a solo maintainer, you cannot supply that approval. Check a
pull request's attribution with:

```bash
gh api repos/einot/agent-kit-skills/pulls/<n>/commits \
  --jq '.[] | "\(.sha[0:7]) \(.commit.author.email) -> \(.author.login // "UNATTRIBUTED")"'
```

## Why the repository is public

Branch protection and rulesets are a paid feature on **private**
repositories: both the classic branch-protection API and the rulesets API
return

```
403 Upgrade to GitHub Pro or make this repository public to enable this feature.
```

Making the repository public was the chosen route to enforcement. The
alternative is GitHub Pro, which allows the same rules while private.

`.github/ruleset-main.json` holds the ruleset payload and
`.github/branch-protection-main.json` the equivalent classic-protection
payload, so the rules can be recreated or moved to another repository
without being re-derived.

## Bypassing, deliberately

No bypass actors are configured, so the rules bind everyone including the
owner. If CI itself breaks and you need to land a fix by hand, either add
yourself as a bypass actor in the ruleset, or set its `enforcement` to
`evaluate` (report-only) and back to `active` afterwards:

```bash
gh api -X PUT repos/einot/agent-kit-skills/rulesets/23732658 -f enforcement=evaluate
```

## Local pre-push guard

Server-side rules are the real enforcement; a local hook just catches the
honest mistake earlier, before a rejected push. `.githooks/pre-push` refuses
a direct push to `main` and runs the validator. Opt in with:

```bash
git config core.hooksPath .githooks
```

Uninstall with `git config --unset core.hooksPath`. A hook is advisory:
`git push --no-verify` skips it.
