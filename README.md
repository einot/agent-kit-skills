# agent-kit — a portable multi-agent orchestration system

Seven Claude Code skills that rebuild, in any project, a delegation-based
orchestration system: a top-level session that acts as project manager and
never edits code itself, six subagents with disjoint write scopes, a shared
path-guard hook that enforces those scopes, and the governance rules that
hold it together.

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

Every file is self-contained: the agent definition to write, the
`path-guard.sh` hook source where the agent needs one, the placeholder
table for adapting it, and a verification checklist. Nothing fetches
anything at install time.

## Install

Unzip into a project (or into `~/.claude/skills/` to have the kit
available everywhere):

```bash
unzip agent-kit-skills.zip
mkdir -p <project>/.claude/skills
cp -r agent-kit-skills/skills/* <project>/.claude/skills/
```

Then, in that project, invoke `agent-kit` to install all six agents, the
shared hook and the `CLAUDE.md` governance sections — or invoke a single
`agent-kit-<agent>` skill to install just that one.

Requires `bash` and `jq` on the machine running the session (the path
guard is a bash hook that parses its JSON payload with `jq`).

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
