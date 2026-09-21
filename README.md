# agent-kit — a portable multi-agent orchestration system

Seven Claude Code skills that rebuild, in any project, a delegation-based
orchestration system: a top-level session that acts as project manager and
never edits code itself, six subagents with disjoint write scopes, two
shared guard hooks that enforce those scopes, the `settings.json` wiring
that actually makes the guards fire, and the governance rules that hold it
together.

## What's in the bundle

| Skill | Installs | Writes? |
| --- | --- | --- |
| `skills/agent-kit/SKILL.md` | the whole system + governance rules | — |
| `skills/agent-kit-architect/SKILL.md` | `architect` | docs + schemas only |
| `skills/agent-kit-coder/SKILL.md` | `coder` | implementation only, in a git worktree |
| `skills/agent-kit-test-author/SKILL.md` | `test-author` | tests only, cannot read the code |
| `skills/agent-kit-reviewer/SKILL.md` | `reviewer` | no — JSON findings only |
| `skills/agent-kit-security-auditor/SKILL.md` | `security-auditor` | no — JSON findings only |
| `skills/agent-kit-supervisor/SKILL.md` | `supervisor` | no — JSON findings only |

The two guard hooks are real, executable files rather than source pasted
into a skill:

| File | What it fences |
| --- | --- |
| `skills/agent-kit/hooks/path-guard.sh` | which paths an agent may read or write (Edit/Write/Read/Grep/Glob) |
| `skills/agent-kit/hooks/bash-guard.sh` | a default-deny allowlist over the Bash tool, for an agent that needs read-only inspection tooling and nothing else |

Every skill that needs a guard points at those same two files, so a fix
lands once instead of in four copies. Each skill still carries everything
else it needs: the agent definition to write, the `settings.json` entry
that wires its guard, the placeholder table for adapting it, and a
verification checklist. Nothing fetches anything at install time.

## Install

Unzip into a project (or into `~/.claude/skills/` to have the kit
available everywhere):

```bash
unzip agent-kit-skills.zip
mkdir -p <project>/.claude/skills
cp -r agent-kit-skills/skills/* <project>/.claude/skills/
```

Then, in that project, invoke `agent-kit` to install all six agents, the
shared hooks, the `settings.json` wiring and the `CLAUDE.md` governance
sections — or invoke a single `agent-kit-<agent>` skill to install just
that one.

Requires `bash` and `jq` on the machine running the session (both guards
are bash hooks that parse their JSON payload with `jq`).

## The one thing to get right

Guards are wired in `.claude/settings.json`, scoped per agent with
`SCOPE_AGENT_TYPES`, and **never** in an agent file's `hooks:`
frontmatter. A guard declared in frontmatter did not fire in the
environment this kit came out of — probed three times, including with an
absolute script path — with no error and no warning, so the agent simply
ran unfenced. Whether it fires appears to depend on workspace-trust state
that is invisible from the repository, so it can look enforced on one
machine and do nothing on another.

Two consequences worth knowing before you trust an install:

- Hook configuration is read from the **main checkout**, not from a
  worktree-isolated agent's checkout. A `coder` running under
  `isolation: worktree` is fenced by the main checkout's `settings.json`;
  the copy inside its worktree is inert.
- A config test is not a fired hook. The only evidence a guard works is a
  real dispatch attempting something the policy must refuse, and a refusal
  whose text comes from the guard. The guard in its home project was
  reviewed nine times before anyone noticed it had never once been
  invoked.

## Developing the skills

Every change is checked by `scripts/validate-skills.py`, which runs in CI on
every pull request and push to `main`. It asserts that each
`skills/<name>/SKILL.md` has closed, parseable frontmatter, that its `name`
is a lowercase-hyphen slug matching its directory, that the `description`
is present and within the 1024-character limit, and that the body is not
empty — the failure modes that make a skill silently never load or never
trigger. Run it yourself before pushing:

```bash
python3 scripts/validate-skills.py .
```

It uses PyYAML when importable and falls back to a strict parser for the
`key: value` subset otherwise, so it needs nothing installed. Add `--strict`
to fail on warnings (an unrecognised frontmatter key, a skill the README
never mentions, a stray file under `skills/`) as well as errors.

`main` is protected by the `protect-main` ruleset: changes land through a
pull request whose `validate` check has passed, the branch must be up to
date with `main` before merging, and force-pushes and deletion are refused.
See `.github/PROTECTION.md`.

## The design in one page

- **Separation of write scope.** Exactly one agent may write each kind of
  artifact — interfaces, implementation, tests. No agent can make its own
  work pass by moving the target.
- **Clean-room tests.** `test-author` is blocked from *reading* the
  implementation, so its tests encode the spec rather than the code's
  current behaviour.
- **Enforcement, not instruction.** The boundaries are `PreToolUse` hooks,
  not paragraphs. Where enforcement is impossible (the guard cannot inspect
  Bash, and `coder` needs Bash to run tests) the prompt says so plainly and
  `supervisor` covers the gap.
- **Plans separated from dispatch.** `architect` has no `Agent` tool; it
  hands back ready-to-dispatch briefs and the session dispatches them, so a
  `supervisor` finding is one hop from the human.
- **Verification of the workers themselves.** Every dispatch to a
  write-capable agent is paired with a `supervisor` review that gets the
  literal brief plus the worker's own report and checks both against the
  files on disk. Any finding stops everything and is reported verbatim.

## What it does not give you

- A sandbox: `coder` keeps Bash, so its guard is a strong default plus
  `supervisor`, not containment.
- Protection against a bad brief: a worker that does exactly what a wrong
  brief said passes every check here.
- Test quality: clean-room tests encode the spec — including its mistakes.
