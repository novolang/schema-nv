# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.0.1 — 2026-09-11

The **interface**, before anyone implements it.  Every signature, every
type and every effect row is published; every body is `todo()`, and the
release is stamped `NOT IMPLEMENTED — interface only`.  Adding this
package works and calling it panics.

- Five modules.  `schcompile` turns a schema document into something
  that validates, `schvalidate` runs it and says why an instance did
  not match, `schformat` is the `format` registry, `schvocab` is the
  scope as data, and `scherror` is the fault a bad SCHEMA gets.
- **The core says what it needs and the host fetches it.**  A `$ref`
  names a URI and resolving one means reading a document, which a `core`
  package may not do — so `external_refs` answers the URIs a schema will
  need, the host reads them however it likes, `with_document` registers
  each one, and `missing_refs` is what the fetch loop stops on.  A
  schema that arrives from outside therefore cannot make a program fetch
  a URL: `$ref`-driven request forgery is not a mitigated vulnerability
  but a capability this package does not have.
- **Compile once, validate many.**  Everything fallible is in `compile`
  — the `$ref` graph, every `pattern`, every keyword's shape — so
  `validate` answers a `SchOutput` and never a `Result`.  An instance
  that does not match is not an error; it is the answer.
- **Reasons, not a first failure**, which is the package's row on the
  grid taken literally: a form with six bad fields tells a person about
  six, and an agent whose tool call does not match its schema is told
  everything wrong with it so the next attempt is right rather than one
  step closer.  Every failure names three places — the instance
  location, the path taken through the schema, and that path as a URI,
  which differ exactly when a `$ref` was followed — plus the keyword
  that decided and a message with the offending value in it.  `is_valid`
  is a separate fast path that stops early and builds nothing.
- Both standard output formats, `flag` and `basic`, so an answer from
  this validator can be read by a client using a different one.
- **Annotations are collected**, because `unevaluatedItems` and
  `unevaluatedProperties` are defined in terms of them, and because
  `title`, `description` and `default` are what a form generator wants
  out of a schema.  They come from a validation rather than from the
  schema, since an `if`/`then` schema's annotations depend on the
  instance.  A schema with no `unevaluated*` keyword says so —
  `uses_unevaluated` — and validates without carrying them.
- **The scope is a list a program can read.**  Asserted: core,
  applicator, validation, unevaluated, format-assertion.  Collected and
  never asserted: the content vocabulary, because asserting
  `contentMediaType` means parsing a media type per schema, and the
  meta-data vocabulary, which is annotations by definition —
  `is_annotation_only` is how a reader tells "by design" from "not done
  yet".  Outside entirely: meta-schema validation of the schema itself,
  and every dialect but 2020-12.
- **`format` is an annotation until the caller says otherwise**, which
  is § 7, and an unknown format stays one even in assertion mode, which
  is § 7.2.1 — so `check_format` answers `?Bool`, because a two-valued
  answer would have forced a choice between failing unknown formats and
  passing them and both are wrong.  Built in are the short, unambiguous,
  ASCII grammars; `email`, `uri` and `idn-hostname` arrive through
  `with_format` as a function, each with the package that answers it
  named.
- **`pattern` uses `std.regex`**, with four named differences from
  ECMA-262 rather than an approximation — byte-wise matching, no
  lookaround or backreferences, no `u` flag, no multiline.  The
  linear-time guarantee those omissions buy is worth having here on
  purpose: a schema often arrives from outside, and a validator that
  could be handed `(a+)+b` as a pattern would be a denial-of-service
  surface.
- **No dependencies**, and four things the standard library's JSON value
  cannot carry are written down rather than worked around — `{}` and
  `null` indistinguishable, which is `type`'s whole job; no deep
  equality, which `const`, `enum` and `uniqueItems` are each defined in
  terms of; no indexed array access; and no embedded or wasm tier.  All
  four are filed against the toolchain, and jsonpath-nv found the same
  four independently.

The oracle is the JSON-Schema-Test-Suite;
`tests/schvalidate_tests.nv` is written in its `{schema, tests}` shape,
so the generated run that replaces it when the bodies land is the same
assertions with more of them.  The suite records only whether an
instance was valid and says nothing about what a validator should SAY,
so the output assertions are this package's own claim.
