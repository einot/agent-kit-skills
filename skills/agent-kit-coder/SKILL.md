---
name: agent-kit-coder
description: Install the `coder` subagent — the only agent allowed to write implementation code, running in an isolated git worktree and blocked by a path guard from editing tests, specs, ADRs or schemas. Use when bootstrapping the delegation-based orchestration system in a new project, or when re-installing/repairing the coder agent in an existing one.
---

# agent-kit: coder

Part of the **agent kit** — a set of single-file skills that rebuild a
delegation-based orchestration system in a new project. Install the whole
system with the `agent-kit` skill, or just this agent with this one.

Companions: `agent-kit-architect`, `agent-kit-test-author`,
`agent-kit-reviewer`, `agent-kit-security-auditor`,
`agent-kit-supervisor`.

## What this agent is for

`coder` implements against an interface it did not design and tests it
cannot change. Three constraints make that real rather than aspirational:

1. **Worktree isolation** (`isolation: worktree`) — changes land in the
   agent's own git worktree and reach the parent checkout only when
   explicitly merged, so a half-finished or wrong change never
   contaminates the working tree the session is reasoning about.
2. **A path-guard denylist** on Edit/Write covering every test directory
   and every spec/schema path. A failing test is a finding, not something
   to edit away; an awkward interface is a flag-back to `architect`, not a
   schema edit.
3. **An explicit rule against routing around the guard with Bash.** The
   guard cannot inspect shell commands and this agent keeps Bash so it can
   run tests — so the boundary is stated in the prompt as well as enforced
   where it can be.

## Install

### 1. Write `.claude/agents/coder.md`

Replace every `{{...}}` placeholder (see *Adapt* below) before writing.

````markdown
---
name: coder
description: Implements {{PROJECT}} services, packages and tools ({{CODE_DIRS}}) against the spec, ADRs and JSON-schema interfaces the architect owns, and against tests test-author has written. Runs in an isolated git worktree. Cannot edit tests or the spec/interfaces. Use for filling in a stub module, fixing a bug, or making a failing test pass.
tools: Read, Grep, Glob, Edit, Write, Bash
isolation: worktree
# Path guard: wired in .claude/settings.json, NOT here. `hooks:` is a
# documented frontmatter field, but a guard declared there did not fire
# in the environment this kit came out of -- probed three times, once
# with an absolute script path; no error, no warning, nothing to notice.
# The docs require workspace trust for project-level frontmatter hooks,
# which is the likely cause but is not confirmed. Either way a guard
# here can look enforced on one machine and silently do nothing on
# another. settings.json hooks fired in every test, and they are read
# from the main checkout, not from this agent's worktree -- so the copy
# of settings.json inside the worktree is inert.
---

You are an implementer for {{PROJECT}} (see `{{SPEC_ENTRY}}`). You run in
your own git worktree — changes you make don't touch the parent checkout
unless they're explicitly merged back.

## Scope

You implement code under {{CODE_DIRS}} (and may touch non-test, non-spec
project files like build config, dependency manifests, container files and
CI workflow files when a task genuinely needs it).

You do **not** edit:
- Any test directory, top-level or nested — that's test-author's domain.
- The spec, ADRs, protocol docs or schemas — that's the architect's domain.

A path guard enforces this for the Edit and Write tools. It does **not**
inspect Bash — don't route around the guard by writing to a guarded path
via a shell command; that defeats the point of the boundary you've been
given, even though nothing will stop you mechanically. The same goes for
editing the guard's own configuration: the policy that fences you is read
from the main checkout, so the `.claude/` directory inside your worktree
is not the one in force, and changing it would be an attempt to escape
rather than a fix.

If your Bash is fenced and a command is refused, the refusal is final for
this task. Do not reach the same effect another way — not with a different
spelling, quoting or option order, not with another interpreter, and not
by writing a script, test, config file or build target and then running a
command that picks it up. Each of those is circumvention, whatever the
intent. Stop the part of the work that needs it, finish what does not, and
report the command, why you needed it, and the refusal word for word.

If a test looks wrong, or the interface you're implementing against seems
incomplete or inconsistent with the spec, say so and stop — don't silently
change the test or the schema yourself. Flag it back to whoever spawned
you so the architect or test-author can address it.

## Conventions in this repo

- Every module you fill in already has a docstring citing the spec
  section(s) it implements (e.g. `Spec: section 10, section 11`) —
  implement to that citation, and if you think the citation is wrong, flag
  it rather than quietly ignoring it.
- Match the existing code style ({{STYLE_CONFIG}}).
- Run the relevant test suite for what you touched before considering the
  work done; you have Bash for this. You cannot make a test pass by
  editing the test — if it seems wrong, that's a flag-back, not a fix.
- {{PROJECT_SPECIFIC_CONVENTIONS — e.g. an ongoing opportunistic cleanup:
  "any file you touch for an unrelated reason, also do X; don't open a file
  solely to do X."}}
````

### 2. Install and wire the path guard

**Copy the hook.** `path-guard.sh` is a real file in this bundle at
`skills/agent-kit/hooks/path-guard.sh`. It is the same script every
guarded agent in the kit uses, and it is not a template — copy it, do not
edit it. If another kit skill already installed it, leave it alone.

```bash
mkdir -p .claude/hooks
cp path/to/agent-kit-skills/skills/agent-kit/hooks/path-guard.sh .claude/hooks/
chmod +x .claude/hooks/path-guard.sh
```

Requires `bash` and `jq`. Read its header comment before adapting
anything around it.

**Wire it in `.claude/settings.json` — not in the agent file:**

````json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "SCOPE_AGENT_TYPES='coder' PATH_ROOT='cwd' DENY_GLOBS='{{DENY_GLOBS}}' ${CLAUDE_PROJECT_DIR}/.claude/hooks/path-guard.sh"
          }
        ]
      }
    ]
  }
}
````

Merge this entry into the file's existing `PreToolUse` array rather than
replacing it; each guarded agent in the kit contributes its own entry.

**`PATH_ROOT='cwd'` makes this guard confine the agent to its worktree.**
It says every guarded path must lie inside the calling agent's working
directory, which for a worktree-isolated `coder` is its worktree. Without
it the guard tries the path against the working directory and then against
the project, and the second base matches the **main checkout**: run
directly, the guard with `PATH_ROOT` unset allows a write to
`<main checkout>/packages/…/x.py` from a worktree agent, and with
`PATH_ROOT='cwd'` refuses it.

In a real dispatch that write never reaches the guard. Claude Code's own
worktree check refuses it first — a hook that logged every payload it
received saw the in-worktree edit and nothing for the escape. So today
this is defence in depth: the kit's guard enforces the boundary itself
instead of depending on a harness behaviour that another version or
environment might not share. The same dispatch confirmed the assumption it
rests on — the payload's `cwd` is the worktree — and that the agent can
still write its own files.

Four things about this wiring are load-bearing, and the last one bites
this agent specifically:

- **Never use the agent file's `hooks:` frontmatter.** It is a documented
  field, but a guard declared there did not fire in the environment this
  kit came out of — probed three times, including with an absolute script
  path. No error, no warning; the agent ran completely unfenced. Whether
  it fires appears to depend on workspace-trust state that is invisible
  from the repository, so it can look enforced on one machine and do
  nothing on another. `settings.json` hooks fired in every test.
- **`SCOPE_AGENT_TYPES` is required.** A `settings.json` hook is
  session-wide: it sees calls from every agent and from the top-level
  session. Without the scope, this denylist would also stop the session
  from reconciling `coder`'s work.
- **The scoping is fail-open.** An absent or unlisted `agent_type` passes
  through. That is routing, not a check — an exit 0 for an out-of-scope
  caller is not approval.
- **Hook configuration is read from the main checkout, not from the
  worktree.** `coder` runs under `isolation: worktree`, and it is fenced
  by whatever the *main* checkout's `.claude/settings.json` says at
  dispatch time; the `settings.json` sitting inside its own worktree is
  inert. This was established by experiment: with the policy removed from
  the main checkout only, while the worktree copy still carried it, the
  write was not denied. So a policy change must land in the main checkout
  before the probe that tests it — editing the file the agent can see
  changes nothing.

This one is a **denylist** (`DENY_GLOBS`, no `ALLOW_GLOBS`), unlike
`architect`'s and `test-author`'s allowlists. That is deliberate:
implementation sprawls across build files, CI config and container
definitions that are legitimately in scope, so enumerating what `coder`
may write would be a list that is wrong within a week. The cost is that a
new guarded directory has to be added to the denylist explicitly — see
*Adapt* below.

### 3. Verify

Nothing here can be checked by reading a config file. The only evidence a
guard works is a real dispatch that a real policy refused — and for this
agent the policy that counts is the one in the **main** checkout.

- `bash -n .claude/hooks/path-guard.sh` parses, and the file is executable.
- Dispatch the agent with a throwaway task that tries to edit a test file
  and confirm the write is denied **with a reason whose text comes from
  the path guard**. A refusal that instead mentions "allowed working
  directories" is the platform sandbox, and means this guard never ran.
- Repeat for a spec/schema path — the denylist has to cover both trees,
  and covering one is the common half-installed state.
- Confirm a write to a legitimate implementation path still succeeds.
- Confirm the top-level session can still edit test files. If it cannot,
  `SCOPE_AGENT_TYPES` is missing from the settings entry.
- Confirm `git worktree list` shows the agent working outside the parent
  checkout.

## Adapt to this project

| Placeholder | Meaning | Common value |
| --- | --- | --- |
| `{{PROJECT}}` | Project name | — |
| `{{SPEC_ENTRY}}` | Path a reader should open first | `docs/spec/README.md` |
| `{{CODE_DIRS}}` | Where implementation lives | `packages/`, `services/`, `tools/`, or `src/` |
| `{{DENY_GLOBS}}` | Space-separated write denylist — see below | a Python project: see below |
| `{{STYLE_CONFIG}}` | Where style is defined | `ruff.toml`, `.eslintrc`, `rustfmt.toml`, … |
| `{{MAKE_GATE_TARGETS}}` | Tripwire only: `make` targets the coder may run | `typecheck` |
| `{{PROJECT_SPECIFIC_CONVENTIONS}}` | Standing conventions, or delete | — |

Glob semantics are bash `[[ str == pattern ]]`, so a bare `*` crosses `/`:
`tests/*` matches `tests/unit/test_foo.py`. In a **denylist** that breadth
is what you want — `*/tests/*` denies every nested test directory — so
unlike `test-author`'s allowlists, these may start with `*`. Give each
directory both a bare and a `/*` entry.

`{{DENY_GLOBS}}` is four groups. The first three are the same for every
project; the fourth depends on your toolchain.

1. **Other agents' domains.** `tests tests/* */tests */tests/*`, your
   test kit, and `docs/spec/* docs/adr/* docs/protocol/* schemas/*`.
2. **Agent configuration.** `.claude .claude/* */.claude */.claude/*
   CLAUDE.md */CLAUDE.md CLAUDE.local.md */CLAUDE.local.md .mcp.json
   */.mcp.json`. An agent that can rewrite `settings.json` can rewrite its
   own fence.
3. **Escapes and invisible state.** `/* ../* */../*` — an absolute path or
   a climb out of the worktree — and `.git .git/* */.git */.git/*`, plus
   your virtualenv and bytecode (`.venv/* */.venv/* __pycache__/*
   */__pycache__/*` for Python). Changes there do not show in `git diff`,
   so `supervisor` would never see them.
4. **Anything that changes what a gate executes.** This is the group that
   matters most and varies most. When `coder` runs the test suite, the test
   runner loads files the *test author* owns; when it runs the linter or
   type checker, those load configuration. A file that is picked up
   automatically is a way to run arbitrary code through a gate that looks
   innocent. For Python: `conftest.py */conftest.py test_*.py */test_*.py
   *_test.py sitecustomize.py */sitecustomize.py usercustomize.py
   */usercustomize.py`, the pytest/mypy/ruff/uv configuration files
   (`pytest.ini .pytest.ini pytest.toml .pytest.toml tox.ini setup.cfg
   mypy.ini .mypy.ini .ruff.toml */ruff.toml uv.toml .python-version`,
   each also with `*/`), `pytest pytest/* ruff ruff/* mypy mypy/*` (a local
   package of that name shadows the real tool), `GNUmakefile makefile`
   (make reads either in preference to `Makefile`, so creating one
   replaces the reviewed recipe), and `uv.lock`.

`tests/hooks/fixtures/settings.json` in this bundle has all four groups
filled in for a Python project on uv, and CI proves each entry against the
guard. For another toolchain, the question to ask of every file it reads
is: *would creating or editing this make a gate run something the command
line does not show?*

Add anything else this agent must not rewrite unreviewed:
`.github/workflows/*` if CI changes need a human, a generated-code
directory, an infrastructure state file.

## Worktree isolation

`isolation: worktree` requires the project to be a git repository. What
lands in the worktree has to be merged back deliberately — decide up front
whether the coder commits in its worktree and the session merges, or the
session applies the diff. State that in the brief; a worker that does not
know is a worker that guesses.

Keeping Bash on this agent is what lets it run the tests. Unfenced, it is
also a way around every other rule in this file. The next section is the
fence; it is optional, and it is a tripwire rather than a boundary.

## Optional: a Bash tripwire

### Why this exists

In the project this kit came from, a `coder` in an isolated worktree tried
to run a multi-line Python self-check. The harness's worktree check refused
it — as `uv run python - <<'EOF'`, as `.venv/bin/python - <<'EOF'`, as
`python3 - <<'EOF'` with the venv's site-packages added by hand; six
refusals. The same script then ran as a multi-line `uv run python -c
"..."`. The agent reported that it "did not try to get around it."

Two lessons. A harness check refuses commands it cannot *analyse*, not
capabilities, so a re-spelling passes it. And nothing had told the agent
that re-spelling a refused command *is* getting around it — so it could
describe doing exactly that, sincerely, as not trying.

### What it is — and is not

**No Bash policy can stop an agent from running arbitrary code if it can
write the code a gate runs, and this one does not try.** The test runner
imports the implementation; `coder` writes the implementation. So the
tripwire does three narrower things:

1. **It refuses every route that needs no file edit first**: ad-hoc
   interpreters (`python -c`, `uv run python`, heredocs), multi-line input,
   package installs, network clients, options that write files or load
   code, and any command the guard has no model for.
2. **It makes the remaining routes leave evidence.** Running code the
   policy does not name now requires changing a tracked file (visible in
   `git diff`) or creating an untracked one outside the denied names
   (visible in `git status`). The routes git does not show — `.venv/`,
   `__pycache__/`, `.git/` — are denied by the write fence. This composes
   with `agent-kit-supervisor`: the session hands `supervisor` exactly that
   `git diff` and `git status`.
3. **It removes the ambiguity.** With `DENY_ADVICE='stop-and-report'`,
   every refusal ends with a paragraph saying the refusal is final, that
   re-spelling it, using another interpreter or writing a file a gate picks
   up are all circumvention, and what to report instead. An agent that does
   it anyway cannot plausibly report that it did not try.

It does not see what a gate executes, it is not a sandbox, it does not
preserve evidence of an edit-run-revert, and it does not restrict reading.

### It fits one toolchain

`bash-guard.sh` has rules for `pytest` and `ruff` as `uv run` targets, for
`make` targets, and for git's writing subcommands. That is a Python
project on uv with a `Makefile`. On any other toolchain it will refuse your
gates, because a command it has no model for is refused by design — do not
widen `ALLOW_CMDS` to compensate, which would admit the launchers the
policy exists to close. Either use the no-Bash-fence build and rely on
`supervisor`, or add rules for your toolchain to the guard, with tests.

### On macOS: the bash version

The hooks start with `#!/usr/bin/env bash`, so they run under the first
`bash` on the hook's `PATH` — on a Mac usually `/bin/bash`, which is 3.2.
Under bash 3.2, literal mode lets two control characters, SOH (`0x01`) and
DEL (`0x7f`), through; under bash 5 it refuses them, as the upstream design
requires. Every other literal-mode rule behaves the same on both. The
tripwire leans on literal mode more than anything else in the kit, so on a
Mac prefer a bash 4 or newer for the hooks — for example by naming that
interpreter in front of the script path in the hook command — and then do
what the rest of this kit asks of any wiring change: confirm with a
dispatch that a refused command's text still begins `bash guard:`. The
behaviour suite prints which bash it found, and lists these two cases as
expected failures only when that bash is older than 4.

### The policy

````json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "SCOPE_AGENT_TYPES='coder' LITERAL_ONLY='1' DENY_ADVICE='stop-and-report' ALLOW_CMDS='ls cat head tail wc stat find grep rg jq diff cmp pwd git uv make' ALLOW_GIT_SUBCMDS='status diff log show rev-parse ls-files add commit merge' ALLOW_UV_RUN_TARGETS='pytest ruff' ALLOW_MAKE_TARGETS='{{MAKE_GATE_TARGETS}}' WRITE_DENY_GLOBS='{{DENY_GLOBS}}' ${CLAUDE_PROJECT_DIR}/.claude/hooks/bash-guard.sh"
    }
  ]
}
````

- `LITERAL_ONLY='1'` refuses any character bash would rewrite after the
  guard has looked — quotes, `$`, backticks, braces, globs, redirection,
  newlines — plus NUL and control characters. What the guard approves is
  then exactly what runs. The `uv`, `make`, git-write and `ruff format`
  rules run only in literal mode.
- `WRITE_DENY_GLOBS` is **the same list as the path guard's
  `{{DENY_GLOBS}}`**. It fences what `ruff format` may rewrite and what
  `git add` may stage, so the Bash route and the Edit/Write route cannot
  disagree. Keep them identical.
- Every `uv run` carries `--locked`, and the guard refuses one that does
  not. Make every `uv run` recipe in the `Makefile` do the same, or `make`
  becomes the unlocked route.
- `{{MAKE_GATE_TARGETS}}` are the targets `coder` needs that are not
  `pytest` or `ruff` — the type checker, typically (`typecheck`). Name
  them; do not allow `make` bare.
- **Commits go through a file.** Literal mode refuses quotes, so
  `git commit -m "Fix the widget"` cannot be written, and the attribution
  trailer the harness asks for contains `<`, `>` and `(`, which no quoting
  could carry anyway. The coder writes the whole message, trailers
  included, to `.commit-msg` at its worktree root with the Write tool, then
  runs `git commit -F .commit-msg`. Add `.commit-msg` to `.gitignore`, and
  say so in the coder's brief — an agent that does not know this will
  report that it cannot commit.
- `git commit` refuses `--amend` (it could fold the coder's change into
  someone else's commit), `-n`/`--no-verify` (it skips hooks), `-S` (it
  runs `gpg.program`) and every option not on a short allowlist; `git add`
  refuses `-f`, `-p` and `-i`. A message word beginning with `-` is refused
  too — a documented over-denial.

The full instantiation is the second entry of
`tests/hooks/fixtures/settings.json`, and group J of
`tests/hooks/test_bash_guard_behavior.py` replays the six commands from
the incident against it; each is refused.

## How it fits the rest of the kit

```text
architect ──interface──▶ test-author ──failing tests──▶ coder ──▶ reviewer
                                                         │        security-auditor
                                              supervisor ◀┘  (every dispatch)
```

Every dispatch to `coder` must be paired with a `supervisor` review before
its output is merged, pushed, or handed to another agent — see
`agent-kit-supervisor`.
