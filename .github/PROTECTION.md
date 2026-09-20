# Protecting `main`

The intended rule for this repository is: **nothing reaches `main` except
through a pull request whose `validate` check has passed.**

GitHub will not enforce that here yet. Both the classic branch-protection
API and the newer rulesets API refuse the request on a **private** repository
under a **free** plan:

```
403 Upgrade to GitHub Pro or make this repository public to enable this feature.
```

So the rule is currently a convention. Three ways to make it real, in
increasing order of cost:

## 1. Make the repository public

Branch protection and rulesets are free on public repositories.

```bash
gh repo edit einot/agent-kit-skills --visibility public --accept-visibility-change-consequences
```

## 2. Upgrade the account to GitHub Pro

Keeps the repository private and unlocks protection on it.

## 3. Enforce locally with a pre-push hook

Server-side rules are the only thing that stops a determined push, but a
local hook catches the honest mistake. Not installed by default — see
"Local pre-push guard" below.

## Applying the protection once it is available

Either of these applies the intended rule. They are equivalent; rulesets are
the newer mechanism.

### Ruleset

```bash
gh api -X POST repos/einot/agent-kit-skills/rulesets --input .github/ruleset-main.json
```

### Classic branch protection

```bash
gh api -X PUT repos/einot/agent-kit-skills/branches/main/protection \
  --input .github/branch-protection-main.json
```

Both require `required_approving_review_count: 0`, because a solo maintainer
cannot approve their own pull request — a count of 1 would lock you out of
your own repository. Raise it to 1 as soon as there is a second maintainer.

`enforce_admins` / bypass is left off so that you can still push a fix by
hand if CI itself breaks. Turn it on if you want the rule to bind you too.

## Local pre-push guard

Blocks a direct push to `main` and runs the validator before any push.
Install it with:

```bash
git config core.hooksPath .githooks
```

Uninstall with `git config --unset core.hooksPath`. Because it lives in the
repository, anyone who clones it can opt in the same way. A hook is advisory:
`git push --no-verify` skips it.
