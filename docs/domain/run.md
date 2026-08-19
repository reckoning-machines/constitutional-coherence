# Run Semantics

Status: **CURRENT SCOPED SEMANTIC OWNER**

A Run is one governed execution bound to one exact Version. Run identity is
created when execution is admitted. The Version binding is immutable after Run
creation.

A Run proves what Version it used. It does not select the current Version of a
Branch.

Failed execution may have no Result. Re-execution creates a new Run identity.
