# Version and Branch Semantics

Status: **CURRENT SCOPED SEMANTIC OWNER**

## Version identity

A Version is one immutable content identity. `version_id` identifies exactly
one Version and never means “latest.” Creating a Version does not make it
current for any Branch.

## Branch current Version

A Branch is a continuing line of development. Its `HEAD` is the one Version
currently selected by Branch Authority.

Only Branch Authority may establish or advance `HEAD`. A Run's bound Version,
an API projection, a browser selection, a cache, or a recovery receipt cannot
select current Branch Version.

Historical Branch currentness is answered by immutable Branch-head transition
receipts, not by reading the mutable present Branch row.
