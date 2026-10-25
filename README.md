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
lands once instead of in four copies.

Both hooks **fail closed**: Claude Code blocks a tool call only when a
hook exits 2, so a guard that crashes on input it did not expect would
otherwise allow it. They refuse a payload they cannot read, a path with a
`.` or `..` component, a path outside the policy's root, a guarded path
outside printable ASCII, a search pattern that climbs out of the searched
directory, a Bash command over 2,048 bytes, and a NUL byte anywhere. Tested
by dispatch against the previous version of this kit, a `test-author`
agent read implementation source twice — once through a coverage report,
once through a `Grep` path containing `..` — and wrote a file into the
architect's spec tree. All three are refused now. See `VERIFICATION.md`.

Each skill carries everything else it needs: the agent definition to
write, the `settings.json` entry that wires its guard, the placeholder
table for adapting it, and a verification checklist. The project ends up
with its own copies; nothing is fetched while the agents run.

## Install: ask Claude to incorporate it

The skills are instructions for adapting the kit to a project, not files
that work where they are dropped. So the way to install it is to open
Claude Code in your project and ask it to incorporate the kit from this
repository:

> Incorporate the agent kit from https://github.com/einot/agent-kit-skills
> into this project. Clone the repository, read `skills/agent-kit/SKILL.md`,
> and follow its Install section.

Claude then clones the repository outside your project, reads the
`agent-kit` skill and the six agent skills it points to, and works through
the install steps:

1. copies `path-guard.sh` and `bash-guard.sh` into `.claude/hooks/`,
2. writes the guard wiring into `.claude/settings.json`,
3. writes the six agent definitions into `.claude/agents/`, filling each
   skill's placeholders (source and test directories, gate commands) from
   what it finds in your project, and asking you for what it cannot find,
4. adds the governance sections to `CLAUDE.md`.

To install a single agent, name its skill instead, for example "…and
follow `skills/agent-kit-test-author/SKILL.md`". To get a version you can
reproduce, name a commit or tag as well ("…at commit `<sha>`").

Ask for a **clone**, not a web fetch. The hooks have to arrive byte for
byte, and a web fetch can hand Claude a processed version of a page
rather than the file; a guard that has been paraphrased is not the guard
tested here.

When it is done, review the diff like any other change, with
`.claude/settings.json` first, since that is what decides whether the
guards fire at all (see the next section). Then have Claude run
`agent-kit`'s *Verify the whole system*: a real dispatch that each guard
must refuse is the only proof the install works.

The machine running the session needs `bash` and `jq`: both guards are
bash hooks that parse their JSON payload with `jq`.

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

## The guards are tested here

`tests/hooks/` runs both hooks as real subprocesses — 1,411 cases once
parametrised — feeding each a `PreToolUse` payload and asserting on the
exit status and the refusal text. The "configured" tests run every policy
in `tests/hooks/fixtures/settings.json`, a complete instantiation of the
wiring the skills document, and the alternative `test-author` read
allowlist in `tests/hooks/fixtures/settings-read-allowlist.json`, so a
glob change that opens a hole fails CI rather than someone's project. It
needs Python, pytest, bash and jq:

```bash
python -m pytest tests/hooks -q
```

129 of those cases are **strict expected failures** on every platform,
listed in `tests/hooks/pending_upstream.txt`. They encode gaps the
upstream design has specified and tested but not yet implemented. (Two
upstream decisions this kit departs from on purpose — the command bound
and non-ASCII paths — are tested as the kit decides them; see
`VERIFICATION.md`.) Strict
means that when one is fixed it fails the build until its line is removed
— the list cannot quietly go stale. Three more fail only under bash 3.2;
see below.

This proves the guard *logic*. It does not prove your `settings.json`
reaches the guard; only a real dispatch does that — see `agent-kit`'s
*Verify the whole system*.

**On macOS, mind the bash version.** The hooks start with
`#!/usr/bin/env bash`, so on a Mac they run under `/bin/bash`, which is
3.2. There, the Bash guard's literal mode — the core of the optional
`coder` tripwire — lets two control characters, SOH and DEL, through; bash
5 refuses them. The suite reports which bash it found in its header. Run
it once on the machine that will run your agents.

**On macOS, mind the shell and the filesystem too.** Claude Code runs an
approved Bash command under your login shell, which is zsh on a Mac, not the
bash the guard is written in. zsh runs a command for `=(cmd)`, for a glob
qualifier such as `*(e:cmd:)`, and for `~[name]`, none of which bash reads that
way, so `bash-guard.sh` refuses a parenthesis or `~[` outside quotes. Claude
Code's own shell setup may also define `grep`, `find` and `rg` as functions
that run ugrep, bfs and ripgrep (observed with `whence -w`/`functions` in a
Bash tool call on macOS), so the guard refuses ugrep's command-running and
config options for `grep` and bfs's `-rm` for `find`; it does not rely on
those functions' own filtering, which can change with any release. And the
default macOS volume is case-insensitive, so `path-guard.sh` folds case when it
matches `DENY_GLOBS` (`.GITHUB/x.yml` is `.github/x.yml`); `ALLOW_GLOBS` and
`EXEMPT_GLOBS` stay exact. Because the volume folds Unicode case too, which
no bash glob reproduces, a guarded path outside printable ASCII is refused. All of these were found on deployments; see
`VERIFICATION.md`.

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
  not paragraphs. The path guard sees only Edit and Write, so the
  recommended `coder` has no Bash and the session runs its gates. Where a
  project keeps Bash on `coder` anyway, enforcement is impossible, the
  prompt says so plainly and `supervisor` covers the gap.
- **Plans separated from dispatch.** `architect` has no `Agent` tool; it
  hands back ready-to-dispatch briefs and the session dispatches them, so a
  `supervisor` finding is one hop from the human.
- **Verification of the workers themselves.** Every dispatch to a
  write-capable agent is paired with a `supervisor` review that gets the
  literal brief plus the worker's own report and checks both against the
  files on disk. Any finding stops everything and is reported verbatim.

## What it does not give you

- A sandbox: nothing is OS-enforced. A `coder` that keeps Bash has a guard
  that is a strong default plus `supervisor`, not containment; the no-Bash
  `coder` closes that route, but the session that runs its gates is not
  sandboxed either.
- Protection against a bad brief: a worker that does exactly what a wrong
  brief said passes every check here.
- Test quality: clean-room tests encode the spec — including its mistakes.

## What has been verified

[VERIFICATION.md](VERIFICATION.md) records which of this kit's claims were
tested by dispatching real subagents against a real install, which were
tested only as guard logic, and which are still untested. It also records
the two defects that testing found. The kit's own argument is that an
untested guard is an assumption, so it seemed wrong not to say which of
these are which.

## License

MIT — see [LICENSE](LICENSE). The point of this bundle is that it is
copied into your own project and adapted there, so the license is the
permissive one that lets you.
