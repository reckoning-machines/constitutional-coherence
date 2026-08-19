# Constitutional Coherence: a working reference

This repository is a small, runnable example of an idea from the essay
[**An Agentic Coding Proposal: Constitutional Coherence**](https://reckoningmachines.substack.com/p/an-agentic-coding-proposal-constitutional).

You can read the whole thing without knowing the vocabulary. This page explains
it in plain language first, then shows you what to run.

## The problem, in one paragraph

Tests check what your software *does*. They do not check who is allowed to
*decide* things. So an agent can add a perfectly reasonable-looking field, ship
it green, and quietly create a second place in the system that answers the same
question, "which version is this branch on?", with a different answer. Nothing
fails. Nothing warns you. Six months later two parts of the system disagree and
nobody can say which one is right, because both of them are, locally.

The essay's name for this is **duplicate authority**, and its claim is that this
is the failure mode that matters once code is cheap to produce.

## The idea, in plain language

Pick the facts in your system that actually matter, the ones where being wrong
changes behavior. For this demo there are five, things like "what version is
this branch currently on" and "what version did this run actually use".

For each one, write down:

- **What is it?** (ontology: what exists, and what makes it that thing)
- **What does it mean?** (semantics: one owner, in prose, in `docs/domain/`)
- **Who decides it?** (authority: exactly one owner, one place it can change)

Then write down every *other* copy of that fact that exists: the API response,
the browser's local state, the audit log. Label each one with what it is
allowed to be. It can be a **derived** view, a **cache**, an immutable
**receipt**, dead **legacy** data, or throwaway **ephemeral** UI state. What it
may never be is a second opinion.

> Copying data is fine. Copying *decision-making* is not.

That's the whole rule. Everything else is machinery for checking it.

## What's in here

The demo app is deliberately boring: Versions exist, a Branch points at one of
them, Runs pin the exact Version they used, Results are frozen to their Run. The
app isn't the point. The point is that all of it is written down and checked.

```text
docs/constitution/     the rules, and the machine-readable map of who decides what
docs/domain/           plain-English meaning of each concept, one owner each
docs/decisions/        records that grant authority to change something
docs/work/changes/     one worked example of a change, start to finish
src/coherence_demo/    the small Branch/Version/Run/Result app
constitutional/        the checker: observe, measure, validate
tests/constitutional/  changes the system must refuse to accept
tests/product/         ordinary behavioral tests
```

The map is [`docs/constitution/authority-topology.yaml`](docs/constitution/authority-topology.yaml).
It says, per fact: who owns it, which database column carries it, which
functions may write it, where its history lives, and which other copies are
allowed to exist.

## Run it

Python 3.11 or newer.

```bash
python -m pip install -e '.[dev]'

python -m constitutional.discover --root .   # what durable state exists?
python -m constitutional.measure  --root .   # what changed since the baseline?
python -m constitutional.validate --root .   # is any of it unauthorized?
pytest
constitutional-coherence-demo
```

## Try breaking it

`tests/constitutional/adversarial/` holds patches that *look* fine and must be
rejected anyway: a second durable copy of the branch head, an unauthorized
function writing to it, browser code reaching into the database to decide which
version is current, history being reconstructed from mutable present state.

`tests/constitutional/gate/` holds a second kind: changes that are refused
because of *how they were proposed*, not what they contain.

`tests/constitutional/blindspots/` holds a third kind, and the most useful one:
changes that are genuinely unconstitutional and are **accepted anyway**. Each
one asserts that validation reports nothing, and explains why. See
[What this does not do](#what-this-does-not-do).

All three are plain YAML. Adding your own case takes about ten lines, and that
is the most useful thing you can do with this repository.

---

# The part the essay leans on hardest: the loop

The essay argues that agentic development should be a **closed loop**:

```text
Audit  ->  Plan  ->  Implement  ->  Verify
                        ^              |
                        +---- mismatch +
```

Plan says what constitutional change is authorized. Implement stays inside it.
Verify measures what actually happened. If they disagree, you go back to Audit,
and, crucially, *the agent doing the implementing does not get to resolve the
disagreement by rewriting its own forecast.*

That last sentence is the entire load-bearing claim. It is also the easiest
thing in the world to get wrong, because the natural way to build it is not a
loop at all: a "what I planned" file next to a "what I did" file. Both files are
text. The same agent writes both, in the same commit. Comparing them proves
nothing.

So the harness here does three specific things.

### 1. Verify reads the repository, not the Plan

`python -m constitutional.measure` reconstructs the repository as it was at a
baseline commit, observes it, observes the working tree, and **subtracts**. What
comes out is the actual delta: which governed facts moved, which writers
appeared, which representations were added or quietly reclassified.

It never opens `constitutional-delta.yaml`. It cannot be talked into agreeing
with a forecast, because it has not read one.

### 2. The authorizing decision must pre-date the change

A Plan cites a decision record that grants it authority. The gate checks that
this record **existed at the baseline commit and was not edited by this change**.

Without that check, "authorized by a legitimate decision" collapses into "the
agent wrote a file saying it was allowed to." With it, the authorization has to
come from outside the change.

### 3. The change record is chosen by the diff

The gate looks at what actually changed, works out which change record that
belongs to, and validates *that* one. Touch governed code with no open change
record and it fails. Touch it under two records and it fails. Attach new work to
a change already marked `COMPLETED` and it fails.

The alternative, pointing the validator at a fixed path, means a change that
never writes a record is a change nobody checks.

## What this does not do

The essay does not have a limitations section. It should, so this repository has
one, and the honest version is not short.

These limitations are not prose. Each one is a fixture in
`tests/constitutional/blindspots/` that introduces a real violation and asserts
that the harness says nothing. If the harness ever improves, those tests fail
and tell you to move the fixture into `adversarial/` and delete the caveat here.

| What slips through | Why | Fixture |
|---|---|---|
| A second durable Branch HEAD in a column named `release_pointer` | discovery only recognises names matching `durable_column_patterns` | `renamed_durable_carrier` |
| An unauthorized `UPDATE branches SET head_version_id` built with an f-string | writer detection reads SQL string *literals*; an f-string is not one | `dynamic_sql_writer` |
| Browser code choosing which Version is current, in a function called `effective_head` | the rule is a hardcoded list of verbs | `renamed_client_decision` |
| The same duplicate HEAD carrier, in a `.sql` file the topology does not list | discovery reads only the files it was told about | `unlisted_schema_file` |
| The `results` immutability trigger deleted, its wording left in a comment | the check asks whether a phrase appears in the schema text | `commented_immutability_trigger` |

The last one deserves its own sentence, because it inverts the argument this
repository is making: the constitutional check passes, and the ordinary
behavioral test in `tests/product/` is what catches it.

Compare `renamed_durable_carrier` against `adversarial/duplicate_head_pointer`,
or `dynamic_sql_writer` against `adversarial/unauthorized_head_writer`. In each
pair the pathology is the same and only the spelling differs. One is refused and
one is not.

**So the checker does not understand your system.** It compares your repository
against a map that a human wrote. It is very good at noticing that the two have
drifted apart, and completely blind to anything the map never mentioned and the
patterns never matched. The topology is doing the thinking; the tool is doing
the bookkeeping.

**The harness does not police itself.** `constitutional/`, `tests/`, and
`.github/` are not governed paths, because a gate cannot meaningfully gate its
own source. In a real deployment you protect those with review ownership rules.

**Completed changes cannot be re-verified.** Measuring a delta needs the state
before the change, which means a commit. `CHANGE-042` predates the measuring
harness, so it is marked `COMPLETED` and retained as documentation rather than
re-checked. The gate refuses to let new work hide behind it.

**Nothing here is a proof.** The useful question is not "is this airtight",
because it isn't. It is "can an ordinary patch introduce a second authority
without anyone noticing?" With a written-down topology and this gate in front of it, the
answers get meaningfully harder to fake. That is the claim, and it is smaller
than the one you might read into the essay.

## Where to look first

If you read three files, read these:

1. [`docs/constitution/authority-topology.yaml`](docs/constitution/authority-topology.yaml): the map. This is the artifact the idea lives or dies on.
2. [`tests/constitutional/adversarial/`](tests/constitutional/adversarial/) and [`tests/constitutional/blindspots/`](tests/constitutional/blindspots/): what the harness catches, and what it misses, side by side.
3. [`constitutional/measure.py`](constitutional/measure.py): the part that makes the loop closed rather than merely described.
