# schema-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`.  Installing this package works;
calling it panics with `not implemented`.

## What this is

JSON Schema 2020-12, over the standard library's JSON value, **with
reasons**.  A schema compiles once; instances validate many times; and
an instance that does not match comes back with a list of failures, each
one naming where in the document, where in the schema, and which
keyword.

```
/users/2/age: 17 is less than the minimum of 18
/users/2:     required property "email" is missing
```

Five modules.

| surface | module | reach for it when |
| --- | --- | --- |
| the **compile** | `schcompile` | you are turning a schema document into something that validates |
| the **validation** | `schvalidate` | you are checking instances and reporting why |
| the **formats** | `schformat` | you want `format` to assert, or to add one |
| the **scope** | `schvocab` | you need to know what this validator checks |
| the **faults** | `scherror` | you are telling somebody their *schema* is wrong |

## Adding it, and checking it

```bash
novo pkg add schema-nv          # into your novo.toml
novo pkg build                  # type- and effect-check the package
novo test --isolate tests/schvalidate_tests.nv
```

`novo test` is red today and that is the point of the release: every
assertion fails with `not implemented: schema-nv.<module>.<fn>`.  They
turn green one at a time as bodies land.

## The one example that will work

```novo
use std.json
use schcompile
use schvalidate

fn main() [io]
    match json.parse("{\"type\":\"object\",\"required\":[\"id\"]}")
        None       =>
            println("not json")
        Some(sdoc) =>
            match schcompile.compile(sdoc)
                Err(f) =>
                    println("bad schema at ${f.schema_location}")
                Ok(s)  =>
                    match json.parse("{\"name\":\"ada\"}")
                        None    => println("not json")
                        Some(i) =>
                            for e in schvalidate.validate(s, i).errors
                                println(schvalidate.error_text(e))
                            // : required property "id" is missing
```

## The load-bearing interface

`schcompile.external_refs` — the core says what it needs, the host
fetches it.

JSON Schema's `$ref` names a URI, and resolving one means **reading a
document**, which is exactly what a `core` package may not do.  So the
package does not resolve anything; it says what it would need:

```novo norun:pseudo
let wanted = schcompile.external_refs(doc)      // core: "these URIs"
// the host reads each one, however it likes
let reg    = schcompile.with_document(reg, uri, fetched)
let schema = schcompile.compile_with(doc, reg)
```

`schcompile.missing_refs` is what the loop stops on, because a fetched
document may have `$ref`s of its own.

This is [`docs/publishing.md`'s](https://novo-lang.org/docs/publishing.html#design)
third sans-IO shape — the core asks, the host performs — and it is the
same one tera-nv's template set has for `{% extends %}`.  It also makes
the package **safe by construction**: a schema that arrives from outside
cannot make a program fetch a URL, because the program decides what it
fetches and this package has no `[net]` to do it with.  Server-side
request forgery through `$ref` is not a vulnerability that was
mitigated; it is a capability that does not exist.

The second half of the shape is **compile once, validate many**.
Everything expensive and everything fallible is in `compile`: the `$ref`
graph, every `pattern`, every keyword's shape.  `validate` then cannot
fail — it answers a `SchOutput`, not a `Result`, because an instance
that does not match is not an error, it is the answer.

The agent tier is why that matters: a tool whose arguments are described
by a schema validates one call at a time, and should not re-read the
schema on every one.

## Reasons, not a first failure

The row on the grid says *"validation with reasons; the agent tier wants
it"*, and the whole output shape follows from taking that literally.

A form with six bad fields should tell a person about six.  An agent
handed a tool call that does not match its schema should be told
everything wrong with it, so its next attempt is *right* rather than one
step closer.  So `validate` collects every failure, and `is_valid` is
the separate fast path for a caller that only wants the boolean — it
stops at the first failure, builds no locations, and collects no
annotations.

Every failure names three places, which is 2020-12 § 12.3's output unit:

| field | what it is |
| --- | --- |
| `instance_location` | where in the document — `/users/2/age` |
| `keyword_location` | the path taken through the schema, with `$ref` as a step |
| `absolute_keyword_location` | the same as a URI, so it names the resource a `$ref` led into |

The last two differ exactly when a `$ref` was followed, and that is the
case where a reader needs both: one says how the validator got there,
the other says where "there" is.

`schvalidate.errors_at` and `failed_locations` are the two questions a
form renderer asks; `flag_output` and `basic_output` are 2020-12's own
output formats, so an answer from this validator can be read by a client
using a different one.

## What is in scope, and what is not

`schvocab` is that answer **as data** rather than as prose, because a
validator that implements "most of" JSON Schema is one nobody can trust
a schema to: the keywords it skips are silently annotations, and a
schema that depended on one passes everything.

**Asserted**: core, applicator, validation, unevaluated, and
format-assertion for the formats below.  That is the whole of what makes
a schema mean something about an instance — `type`, `enum`, `const`, the
numeric and string and array and object keywords, `allOf` / `anyOf` /
`oneOf` / `not`, `if` / `then` / `else`, `properties` /
`patternProperties` / `additionalProperties` / `propertyNames`,
`prefixItems` / `items` / `contains`, `$ref`, `$dynamicRef`, and both
`unevaluated*` keywords.

**Collected as annotations, never asserted**, and each is a decision:

- **The content vocabulary** — `contentEncoding`, `contentMediaType`,
  `contentSchema`.  2020-12 § 8.5 makes these annotations by default and
  an implementation *may* assert them.  Asserting `contentMediaType:
  application/xml` means parsing XML, and a validator that dragged in a
  parser per media type would be a different package.
- **The meta-data vocabulary** — `title`, `description`, `default`,
  `examples`, `deprecated`, `readOnly`, `writeOnly`.  Annotations by
  definition, and listed so a reader can tell "annotation by design"
  from "not done yet".  `schvocab.is_annotation_only` is that
  distinction as a function.

**Outside entirely:**

- **Meta-schema validation of the schema itself.**  A schema is not
  checked against the 2020-12 meta-schema before it is used.  `compile`
  catches what it needs to catch in order to run — a `type` that is not
  a type, a `$ref` that does not resolve, a `pattern` that does not
  compile — and not every way a schema can be unusual.  A caller who
  wants the full check registers the meta-schema as a document and
  validates their schema *with this package*, which is what a
  meta-schema is for and costs this package nothing.
- **Every dialect but 2020-12.**  2019-09 and draft-07 are close and are
  not the same — `items` means different things in 2020-12 and 2019-09 —
  and a schema read under the wrong dialect changes meaning without
  changing shape.  A `$schema` naming another one is
  `SchUnknownDialect`.

## `format` is an annotation until you say otherwise

2020-12 § 7 makes `format` an annotation unless the schema declares the
format-assertion vocabulary, and this package follows it.  A validator
that refused a string because its `format` said `email` would refuse
documents every other implementation accepts.

Built in are the formats whose grammar is short, unambiguous and ASCII —
a check a reader can verify against the RFC in a minute: `date`, `time`,
`date-time`, `duration`, `uuid`, `ipv4`, `ipv6`, `json-pointer`,
`relative-json-pointer`, `hostname`, `regex`.

Not built in, each with the package that answers it: `email` and
`idn-email` (RFC 5322's addr-spec is famously not a regular language,
and nobody's five-line check is right), `uri` / `uri-reference` / `iri`
(url-nv's parser is the answer, and depending on it here would put a URL
parser in the closure of every schema that never mentions one),
`idn-hostname` (punycode-nv and IDNA's tables), `uri-template` (RFC 6570
is a language of its own).  `schformat.with_format` takes a
`fn(Str) -> Bool`, so a caller registers what it needs.

**A format nobody knows stays an annotation even in assertion mode** —
§ 7.2.1 says an implementation must not fail a value for a format it
does not implement.  That is why `check_format` answers `?Bool` and not
`Bool`: a two-valued answer would have forced a choice between failing
unknown formats and passing them, and both are wrong.

## `pattern` is ECMA-262, and `std.regex` is not quite

`pattern` and `patternProperties` are ECMA-262 regular expressions.
This package uses `std.regex`, which is prepended to every program,
effect-free and available at every tier — so there is no dependency and
no caller-supplied engine.  Where the dialect differs, named rather than
approximated:

- **Matching is byte-wise, not code-point-wise.**  `.` is any byte but a
  newline, and `\d` and `\w` are ASCII.  A pattern over non-ASCII text
  behaves differently from a JavaScript engine's.
- **No lookahead, lookbehind or backreferences.**  `std.regex` is a
  Thompson NFA with a linear-time guarantee, and those three are what
  the guarantee costs.  A schema using one is `SchBadPattern` rather
  than a silent mismatch.
- **No `u` flag and no `\p{...}`.**
- `^` and `$` anchor the whole subject; there is no multiline mode.

The linear-time guarantee is worth having on purpose here: a schema is
very often a thing that arrives from outside, and a validator that could
be given `(a+)+b` as a `pattern` would be a denial-of-service surface.

## What the standard library's JSON value cannot carry

This package validates `std.json`'s value — `JsonValueH` — on purpose: a
second JSON value type would mean every caller converting a document
before it could be checked.  What that costs:

**`{}` and `null` are the same value to every accessor.**  Both answer
zero keys and `None` from every `to_*`.  Only `json.stringify` separates
them — and `type` is the most-used keyword in JSON Schema, so
`{"type": "object"}` against `{}` and against `null` is the difference
this package most needs and least has.  Every node reached has to be
discriminated, so the workaround is a rendering per node rather than a
one-off.

**There is no deep equality.**  `const`, `enum` and `uniqueItems` are
all defined as JSON value equality, structurally, with `1` and `1.0`
equal.  `stringify`-and-compare gets both of those wrong.

**Reaching one element of an array materialises all of it**, so
`uniqueItems` over a 100,000-element array is quadratic in allocations
rather than in comparisons.

**`std.json` is refused on the embedded tier and has no wasm runtime**,
so this package makes no device claim and does not run in a browser.

All four are filed against the toolchain as
`std-json-cannot-tell-an-empty-object-from-null-and-has-no-deep-equality`,
with `json.type_of`, `json.is_null` and `json.equals` as the smallest
things that would close them.  jsonpath-nv found the same four
independently; they are one fix.

## The layer, and why

`core`.  A walk over a schema the caller parsed and an instance the
caller parsed, with `$ref` resolution against documents the caller
registered.  No function declares an effect, and the one place an effect
could have crept in — fetching a `$ref` — is the interface above rather
than a capability.

## The reference implementation

`jsonschema` (Python, MIT) and pydantic's validation half for the shape
of the API; the specification itself for the behaviour.  The oracle is
the **JSON-Schema-Test-Suite** — the community suite the specification's
authors maintain, a list of `{schema, tests: [{data, valid}]}` groups,
one file per keyword.  `tests/schvalidate_tests.nv` is written in that
shape, so the generated run that replaces it when the bodies land is the
same assertions with more of them.

The suite records only whether an instance was valid, and says nothing
about what a validator should *say* when it was not — so the output
assertions in the middle of that file are this package's own claim, and
the ones a reviewer should read hardest.

## Status

| function | implemented |
| --- | --- |
| `scherror.fault`, `.kind_name`, `.message` | no |
| `schvocab.vocabulary_uri`, `.vocabulary_named` | no |
| `schvocab.is_implemented`, `.is_annotation_only` | no |
| `schvocab.implemented_keywords`, `.unimplemented_keywords` | no |
| `schvocab.keyword_vocabulary`, `.keyword_is_asserted`, `.type_names` | no |
| `schcompile.default_options`, `.registry`, `.with_document`, `.document_uris` | no |
| `schcompile.external_refs`, `.missing_refs` | no |
| `schcompile.compile`, `.compile_with`, `.compile_with_options`, `.faults` | no |
| `schcompile.resource_ids`, `.unsupported_vocabularies` | no |
| `schvalidate.validate`, `.validate_with`, `.is_valid` | no |
| `schvalidate.first_error`, `.errors_at`, `.failed_locations`, `.error_text` | no |
| `schvalidate.flag_output`, `.basic_output` | no |
| `schvalidate.annotations_at`, `.annotation` | no |
| `schformat.formats`, `.builtin_formats`, `.with_format`, `.without_format` | no |
| `schformat.has_format`, `.format_names`, `.check_format`, `.unsupported_formats` | no |
