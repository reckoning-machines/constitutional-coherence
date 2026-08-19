# Result Semantics

Status: **CURRENT SCOPED SEMANTIC OWNER**

A Result is the immutable canonical outcome of one successful Run. Its exact
identity is `ResultsRef(run_id)`: the producing Run identifier interpreted by
Result Authority within trusted application scope.

One Run has zero or one Result. Result content cannot be changed after
publication. A display projection may repeat Result content but cannot create,
replace, or select canonical Result truth.
