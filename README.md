# Constitutional Coherence: a working reference

A small, runnable implementation of the framework set out in
[An Agentic Coding Proposal: Constitutional Coherence](https://reckoningmachines.substack.com/p/an-agentic-coding-proposal-constitutional).

The essay argues that once code is cheap to produce, the binding constraint is
no longer writing software but preserving the intent of the system you already
have. This repository is the argument in executable form, including the places
where it does not hold.

## The exposure

Every firm that has run two systems against the same position knows the failure.
Both books say they are the record. Neither is wrong locally. The discrepancy
surfaces at the worst moment, and the reconciliation costs more than either
system did.

Software acquires the same exposure quietly. A test suite confirms that the
software does what it is supposed to do. It says nothing about who is entitled
to decide. An agent adds a reasonable field, the suite passes, and the system
now holds two answers to a single question: which version is this branch on. Six
months on, two components disagree, and no one can adjudicate, because both
positions are defensible.

The essay calls this duplicate authority. It is the exposure this repository is
built to test for.

## The control

Identify the facts where being wrong changes behavior. There are five here,
including which version a branch currently points at, and which version a given
run actually used.

For each one, record three things:

- Ontology. What the thing is, and what makes it that thing.
- Semantics. What it means, in prose, owned by one document in `docs/domain/`.
- Authority. Who decides it, and the single place it may change.

Then record every other copy of that fact that exists: the API response, the
browser's local state, the audit log. Each copy is assigned a standing. It may
be a derived view, a cache, an immutable receipt, dormant legacy data, or
throwaway interface state. It may not be a second opinion.

> Duplicating data is permitted. Duplicating decision rights is not.

That is the entire rule. Everything below is the apparatus for enforcing it.

## Why this example

A trading system is a state machine on steroids. It carries more state than
ordinary software, moves it faster, keeps it longer, and pays a great deal more
for ambiguity about which copy is correct. Strip one down to its frame and the
same small skeleton is always there.

| In this repository | In a trading system |
|---|---|
| Version | an immutable model, strategy or risk configuration, identified by its content |
| Branch head | the configuration that is live right now |
| Run | one execution bound to one exact configuration: a valuation, a risk cycle, an order generation pass |
| Result | the output sealed to that run: a mark, a P and L figure, a fill |
| Branch head events | the record of when the live configuration changed, and to what |

That skeleton is why this example is not a toy. It is the smallest arrangement
that can still be asked the questions a trading system gets asked:

- Which model was live at 14:32:07, when this trade printed? Not which model is
  live now.
- Which exact configuration produced this mark, and can it be produced again
  next quarter, after the configuration has moved on eleven times?
- The risk system and the execution system disagree about the current version.
  Which one is entitled to be right?

None of these are questions about behavior, so no test suite asks them. All
three are questions about authority and about time. Each is answerable here, and
each answer is a named column with a named owner, rather than an inference.

The failure mode is equally familiar. A failover cache is added, sensibly, and
persists a head version of its own. Nothing breaks. Both values are defensible.
Nothing in the system is willing to say which one governs. That is why versions
and results carry content hashes, why runs and results cannot be updated in
place, and why the history of the live pointer is kept as receipts rather than
inferred from the pointer's present value. Those are books and records
properties before they are engineering ones.

## Contents

The application is small on purpose. Versions exist, a branch points at one,
runs record the exact version they used, and results are sealed to their run.
The application is not the subject. The subject is that all of it is written
down and tested against.

```text
docs/constitution/     the rules, and a machine-readable map of who decides what
docs/domain/           what each concept means, one owner per concept
docs/decisions/        the records that grant authority to change something
docs/work/changes/     one worked example of a change, start to finish
src/coherence_demo/    the branch, version, run and result application
constitutional/        the checker: observe, measure, validate
tests/constitutional/  changes the system is required to refuse
tests/product/         ordinary behavioral tests
```

The map is
[`docs/constitution/authority-topology.yaml`](docs/constitution/authority-topology.yaml).
For each governed fact it names the owner, the database column that carries it,
the functions permitted to write it, where its history is kept, and which other
copies are sanctioned.

## Running it

Python 3.11 or later.

```bash
python -m pip install -e '.[dev]'

python -m constitutional.discover --root .   # what durable state exists
python -m constitutional.measure  --root .   # what has changed since the baseline
python -m constitutional.validate --root .   # is any of it unauthorized
pytest
constitutional-coherence-demo
```

## Testing the controls

Three sets of test cases, all plain YAML.

`tests/constitutional/adversarial/` holds changes that look reasonable and must
be refused anyway: a second durable copy of the branch head, an unauthorized
function writing to it, browser code reaching into the database to decide which
version is current, history reconstructed from mutable present state.

`tests/constitutional/gate/` holds changes refused on procedural grounds rather
than on their contents.

`tests/constitutional/blindspots/` holds the cases that matter most: real
violations that the checker accepts. Each asserts that validation reports
nothing, and states why. See [Control gaps](#control-gaps).

Adding a case takes about ten lines, and is the most useful thing you can do
with this repository.

## The control that was missing

The essay specifies a closed loop.

```text
Audit  ->  Plan  ->  Implement  ->  Verify
                        ^              |
                        +---- mismatch +
```

Plan states the constitutional change being authorized. Implement stays inside
it. Verify measures what actually happened. A discrepancy returns the work to
Audit, and the party doing the implementation does not get to settle the
discrepancy by restating what it intended.

An auditor would recognize the risk immediately. If the same party writes both
the forecast and the result, and the two are compared only against each other,
nothing has been verified. That was the original arrangement here: a file
recording what was planned, and a file recording what was done, adjacent in the
same directory, written by the same agent in the same commit.

Three controls now stand behind it.

### Verify measures the repository

`constitutional/measure.py` reconstructs the repository as it stood at a
baseline commit, observes both that state and the working tree, and takes the
difference. The output is the change that actually occurred: which facts moved,
which writers appeared, which copies were added or quietly reclassified.

It does not read the plan. It cannot be talked into agreeing with a forecast it
has never seen.

### Authorization has to pre-date the work

A plan cites a decision record that grants it authority. The check confirms that
the record existed at the baseline and was not edited by the change it
authorizes.

Without that, "authorized by a legitimate decision" reduces to an agent writing
a note giving itself permission.

### The change record is selected by the diff

The check reads what actually changed, determines which change record covers it,
and validates that one. Governed code touched with no open record fails. Two
open records fail. Work attached to a record already closed fails.

Pointing the validator at a fixed path, as it did before, means any change that
never files a record is a change nobody reviews.

## Control gaps

The essay does not carry a limitations section. This repository does, and the
honest version is not short.

The gaps below are not prose. Each is a test case in
`tests/constitutional/blindspots/` that introduces a genuine violation and
asserts that the checker says nothing. Should the coverage ever improve, those
tests fail and instruct the reader to reclassify the case and delete the
disclosure here.

| Accepted today | Why | Case |
|---|---|---|
| A second durable branch head in a column named `release_pointer` | discovery recognizes only names matching `durable_column_patterns` | `renamed_durable_carrier` |
| An unauthorized `UPDATE branches SET head_version_id` assembled with an f-string | writer detection reads SQL held as string constants, which an f-string is not | `dynamic_sql_writer` |
| Browser code choosing the current version, in a function called `effective_head` | the rule is a fixed list of verbs | `renamed_client_decision` |
| The same duplicate carrier, in a `.sql` file the map does not list | discovery reads only the files it was told about | `unlisted_schema_file` |
| The `results` immutability guard deleted, its wording left in a comment | the check asks whether a phrase appears in the schema text | `commented_immutability_trigger` |

The last one runs against the position this repository is taking. The
constitutional check passes it. The ordinary behavioral test in
`tests/product/` is what catches it.

Set `renamed_durable_carrier` beside `adversarial/duplicate_head_pointer`, or
`dynamic_sql_writer` beside `adversarial/unauthorized_head_writer`. Within each
pair the violation is identical and only the wording differs. One is refused and
one is not.

**The checker does not understand the system.** It compares the repository
against a map a person wrote. It is reliable at detecting that the two have
drifted apart, and blind to anything the map never covered and the patterns
never matched. The map does the reasoning. The tool keeps the books.

**The tooling is outside its own perimeter.** `constitutional/`, `tests/` and
`.github/` are not governed paths, since a check cannot meaningfully police its
own source. In production that exposure is covered by review ownership rules.

**Closed changes cannot be re-measured.** Measuring a change requires the state
that preceded it, which means a commit. `CHANGE-042` predates the measuring
tooling, so it is marked complete and retained as documentation rather than
re-tested. New work cannot be attached to it.

**None of this is a proof.** The question worth asking is not whether the
controls are airtight, because they are not. It is whether an ordinary patch can
introduce a second authority without anyone noticing. With a written map and
this check in front of it, that becomes materially harder to do by accident.
That is the claim, and it is narrower than the essay alone might suggest.

## Where to start

Three files, in order.

1. [`docs/constitution/authority-topology.yaml`](docs/constitution/authority-topology.yaml).
   The map. The framework stands or falls on this document.
2. [`tests/constitutional/adversarial/`](tests/constitutional/adversarial/) and
   [`tests/constitutional/blindspots/`](tests/constitutional/blindspots/). What
   the checker catches and what it misses, side by side.
3. [`constitutional/measure.py`](constitutional/measure.py). What makes the loop
   closed rather than merely described.
