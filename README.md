# schema-nv

JSON Schema is a language for describing the shape of a JSON document,
so that a program can check one against a description.
[JSON Schema 2020-12](https://json-schema.org/draft/2020-12/release-notes)
is the dialect this package implements, over the standard library's JSON
value. A schema is compiled once and instances are validated many times.
An instance that does not match comes back with every failure, each
naming where in the document, where in the schema, and which keyword
decided.

```
/users/2/age: 17 is less than the minimum of 18
/users/2:     required property "email" is missing
```

**Status: NOT IMPLEMENTED — interface only.** Every function is
declared with its full signature, but every body is a `todo()` that
panics when called. The package is published so its design can be
reviewed and depended on before it is implemented. Version 0.1.0 will
be the first working release.

## What it is

A **schema** is a JSON object whose members are **keywords**, or the
boolean `true` or `false`, which match everything and nothing. An
**instance** is the document being checked.

A keyword belongs to a **vocabulary**, which is a named group of them.
2020-12 splits the language into eight, and a schema may declare which
it relies on.

| Vocabulary | Keywords | Here |
| --- | --- | --- |
| Core | `$id`, `$schema`, `$ref`, `$anchor`, `$dynamicRef`, `$dynamicAnchor`, `$vocabulary`, `$comment`, `$defs` | asserted |
| Applicator | `allOf`, `anyOf`, `oneOf`, `not`, `if`, `then`, `else`, `dependentSchemas`, `prefixItems`, `items`, `contains`, `properties`, `patternProperties`, `additionalProperties`, `propertyNames` | asserted |
| Validation | `type`, `enum`, `const`, the numeric, string, array and object keywords | asserted |
| Unevaluated | `unevaluatedItems`, `unevaluatedProperties` | asserted |
| Format annotation | `format` | collected |
| Format assertion | `format` | asserted for the formats below |
| Content | `contentEncoding`, `contentMediaType`, `contentSchema` | collected, never asserted |
| Meta-data | `title`, `description`, `default`, `examples`, `deprecated`, `readOnly`, `writeOnly` | collected, never asserted |

An **annotation** is something a keyword says about an instance rather
than a condition it imposes. A schema that relies on an annotation for
correctness is a schema that passes everything, so
`schvocab.is_annotation_only` answers which keywords are annotations by
design rather than unfinished.

A **`$ref`** names another schema by URI. Resolving one means reading a
document, which this package does not do. Instead
`schcompile.external_refs` answers which URIs a schema needs, the caller
fetches them however it likes, `schcompile.with_document` registers each
one, and `schcompile.compile_with` uses the registry.
`schcompile.missing_refs` is what a loop stops on, because a fetched
document may have references of its own.

An **output unit** is one failure or one annotation, and it names three
places, which is 2020-12 section 12.3's shape.

| Field | What it is |
| --- | --- |
| `instance_location` | Where in the document, as an RFC 6901 pointer: `/users/2/age` |
| `keyword_location` | The path the validator took through the schema, with `$ref` as a step |
| `absolute_keyword_location` | The same as a URI, naming the resource a `$ref` led into |

The last two differ exactly when a `$ref` was followed. One says how the
validator got there and the other says where "there" is.

## Install

```
novo pkg add schema-nv
```

## Example

```novo
use std.json
use scherror
use schcompile
use schvalidate

fn main() [io]
    match json.parse("{\"type\":\"object\",\"required\":[\"id\"]}")
        None       => println("the schema is not json")
        Some(sdoc) =>
            // Compile once. Everything that can go wrong with the
            // schema goes wrong here.
            match schcompile.compile(sdoc)
                Err(f) => println(scherror.message(f))
                Ok(s)  =>
                    match json.parse("{\"name\":\"ada\"}")
                        None    => println("the instance is not json")
                        Some(i) =>
                            // Validate as often as you like. This
                            // cannot fail: an instance that does not
                            // match is the answer, not an error.
                            for e in schvalidate.validate(s, i).errors
                                // Where in the document, and why.
                                println("${e.instance_location}: ${schvalidate.error_text(e)}")
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a `not implemented:
schema-nv.<module>.<fn>` panic. The tests are the specification the
implementation will have to satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `schcompile` | Turning a schema document into a compiled schema: the registry of other documents, the list of references it needs, the compile, and the options it takes. |
| `schvalidate` | Checking an instance: the output, the fast boolean path, the questions a form renderer asks of a result, the annotations, and the specification's two output formats. |
| `schformat` | The `format` keyword: the formats built in, a registry a caller adds to, and the check itself. |
| `schvocab` | What this validator implements, as data: the vocabularies, which keywords are asserted, and which are annotations by design. |
| `scherror` | Every reason a schema cannot be compiled, each naming where in the schema it is. |

## How to choose an entry point

**`schcompile.compile` takes a schema with no external references.**
One argument, for the ordinary case.

**`schcompile.external_refs`, then `with_document`, then
`compile_with`** is the shape for a schema that references others. The
caller does the fetching.

**`schvalidate.validate` answers every failure.** Use it when a person
or a program has to be told what to fix.

**`schvalidate.is_valid` answers a boolean.** It stops at the first
failure, builds no locations and collects no annotations. Use it when
nothing will be reported.

**`schvalidate.flag_output` and `basic_output`** render a result in
2020-12's own output formats, so a client written against another
implementation can read it.

## The rules a user needs

1. **Compiling can fail and validating cannot.** Everything expensive
   and everything fallible is in the compile: the reference graph, every
   `pattern`, every keyword's shape. `schvalidate.validate` answers a
   `SchOutput` and not a `Result`, because an instance that does not
   match is the answer.
2. **Nothing here fetches a `$ref`.** The package has no `[net]` and no
   `[fs]`, so a schema that arrives from outside cannot make a program
   fetch a URL. A reference to a document the registry does not hold is
   `SchUnresolvedRef` at compile time.
3. **Every failure is reported, not just the first.** A form with six
   bad fields should tell a person about six. `errors_at` and
   `failed_locations` are the two questions a form renderer asks.
4. **`format` is an annotation unless the schema asks otherwise.**
   2020-12 section 7 says so, and a validator that refused a string
   because its `format` said `email` would refuse documents every other
   implementation accepts. `SchOptions.assert_formats` turns assertion
   on for a caller who wants it.
5. **A format nobody knows stays an annotation even in assertion
   mode.** Section 7.2.1 forbids failing a value for a format the
   implementation does not have, which is why
   `schformat.check_format` answers `?Bool`: there is no true or false
   to give.
6. **These formats are built in**, because each has a short,
   unambiguous, ASCII grammar a reader can check against its RFC:
   `date`, `time`, `date-time`, `duration`, `uuid`, `ipv4`, `ipv6`,
   `json-pointer`, `relative-json-pointer`, `hostname`, `regex`.
   `schformat.with_format` takes a `fn(Str) -> Bool` for any other.
7. **`pattern` is an ECMA-262 regular expression, and `std.regex` is
   not quite one.** The differences are named rather than approximated:
   matching is byte-wise, so `.` is any byte but a newline and `\d` and
   `\w` are ASCII; there is no lookahead, lookbehind or backreference,
   and a schema using one is `SchBadPattern`; there is no `u` flag and
   no `\p{...}`; and `^` and `$` anchor the whole subject, with no
   multiline mode.
8. **A `pattern` cannot be a denial of service.** `std.regex` is a
   Thompson automaton with a linear-time guarantee, which is what the
   three missing constructs buy. A schema is often a thing that arrives
   from outside, and `(a+)+b` as a `pattern` would otherwise be a way
   in.
9. **An unknown keyword is an annotation by default.** That is the
   specification's rule. `SchOptions.refuse_unknown_keywords` turns it
   into `SchUnknownKeyword`, which a caller validating its own schemas
   usually wants: `"requred": ["a"]` silently passes everything.
10. **A `$vocabulary` entry this package does not implement, with the
    value `true`, is refused.** 2020-12 section 8.1.2 requires it. An
    entry with the value `false` is a note.
11. **Only 2020-12 is implemented.** A `$schema` naming another dialect
    is `SchUnknownDialect`. 2019-09 and draft-07 are close and not the
    same: `items` means different things in 2020-12 and 2019-09, so a
    schema read under the wrong dialect changes meaning without
    changing shape. `SchOptions.default_dialect` says what a schema
    with no `$schema` is assumed to be.
12. **A subschema that failed contributes no annotations.** 2020-12
    section 7.7.1 drops them, because an annotation from a branch that
    did not apply would describe an instance nobody accepted.
13. **A compile is bounded at 128 levels of nesting by default.**
    `SchOptions.max_depth` moves the line and `SchDepthLimit` is what a
    deeper schema answers.
14. **`{}` and `null` cannot be told apart through this package
    today.** The standard library's JSON accessors answer the same for
    both, and `type` is the most used keyword in the language. The
    defect is filed against the toolchain; see "What is not included".
15. **`scherror.kind_name` is stable across releases.** Programs quote
    the spellings in their own messages and tests.

## What is not included

- **Fetching a referenced document.** See rule 2.
- **Validating a schema against the 2020-12 meta-schema.** A compile
  catches what it must in order to run: a `type` that is not a type, a
  reference that does not resolve, a `pattern` that does not compile. A
  caller who wants the full check registers the meta-schema as a
  document and validates their schema with this package, which is what
  a meta-schema is for.
- **Asserting the content vocabulary.** Asserting
  `contentMediaType: application/xml` means parsing XML, and a
  validator that pulled in a parser for each media type would be a
  different package. 2020-12 section 8.5 makes these annotations by
  default.
- **The formats with long or disputed grammars.** `email` and
  `idn-email`, because RFC 5322's address grammar is not a regular
  language and nobody's short check is right; `uri`, `uri-reference`
  and `iri`, which [url-nv](https://novo-lang.org/packages/url-nv)
  answers; `idn-hostname`, which needs
  [punycode-nv](https://novo-lang.org/packages/punycode-nv) and IDNA's
  tables; and `uri-template`, which is a language of its own in RFC
  6570. `schformat.unsupported_formats` lists them and
  `with_format` is how a caller supplies one.
- **A JSON value type of this package's own.** Instances are
  `std.json`'s value, because a second JSON type in one program would
  mean converting every document before it could be checked.
- **A correct `type` against `{}` and `null`, and a deep equality.**
  `const`, `enum` and `uniqueItems` are all defined by structural
  equality with `1` and `1.0` equal, and rendering and comparing text
  gets that wrong. `json.type_of`, `json.is_null` and `json.equals`
  are the smallest additions to the standard library that would close
  both, filed as
  `std-json-cannot-tell-an-empty-object-from-null-and-has-no-deep-equality`.
- **Cheap access to one array element.** `json.to_list` materialises
  the whole array, so `uniqueItems` over a 100 000-element array is
  quadratic in allocations rather than in comparisons.
- **A microcontroller build, and a browser build.** `std.json` is
  refused on the embedded tier and has no wasm runtime.

## Related packages

- [jsonpath-nv](https://novo-lang.org/packages/jsonpath-nv) selects
  parts of a JSON document by RFC 9535. It answers which parts of a
  document you asked for; this package answers whether the document is
  what it should be. Both select over `std.json`'s value and both are
  blocked by the same four gaps in it.
- [url-nv](https://novo-lang.org/packages/url-nv) and
  [punycode-nv](https://novo-lang.org/packages/punycode-nv) are what a
  caller registers with `schformat.with_format` for the `uri` and
  `idn-hostname` formats.
- `std.json` in the standard library parses and renders JSON and is the
  value this package validates. `std.regex` is the engine behind
  `pattern`; it is prepended to every program, so there is no
  dependency and no caller-supplied engine.

## Tests

```bash
novo test --isolate tests/schcompile_tests.nv    # 5 tests: the compile and the registry
novo test --isolate tests/schvalidate_tests.nv   # 7 tests: the checks and what they say
```

The specification itself is the reference for behaviour, and
`jsonschema` in Python and pydantic's validation half are the references
for the shape of the API. The oracle is the JSON-Schema-Test-Suite, the
community suite the specification's authors maintain: groups of
`{schema, tests: [{data, valid}]}`, one file per keyword.
`tests/schvalidate_tests.nv` is written in that shape, so the generated
run that replaces it when the bodies land is the same assertions with
more of them.

The suite records only whether an instance was valid and says nothing
about what a validator should say when it was not. The assertions about
the messages and the three locations are therefore this package's own
claim, and the ones a reviewer should read hardest.

The tests compile today and fail at run, each on the `not implemented`
panic that is its body. That is the expected state of an interface
release. They turn green one at a time as bodies land.

## Implementation status

Nothing is implemented, apart from the one constant. Every function
here is declared with its signature and its effect row, and every body
is a `todo()`.

| Item | Implemented |
| --- | --- |
| `schvocab.DIALECT_2020_12` | yes (it is a constant) |
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

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
