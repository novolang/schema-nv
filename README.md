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
4. **`format` is an annotation unless a caller asks otherwise.**
   2020-12 section 7 says so, and a validator that refused a string
   because its `format` said `email` would refuse documents every other
   implementation accepts. `schvalidate.validate_with` asserts every
   format the registry it is given knows, and
   `SchOptions.assert_formats` makes `validate` and `is_valid` assert
   the built-in ones.
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
   `hostname` checks RFC 1123's syntax; a label starting `xn--` is
   accepted without checking that its Punycode decodes to a label IDNA
   permits.
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
10. **A `$vocabulary` entry this package does not recognise, with the
    value `true`, is refused.** 2020-12 section 8.1.2 requires it. The
    eight vocabularies of 2020-12 are all recognised, the content and
    meta-data ones as annotations, so the 2020-12 meta-schema compiles.
    An entry with the value `false` is not refused.
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
14. **Numbers compare by value.** `1` and `1.0` are equal for `const`,
    `enum` and `uniqueItems`, and `1.0` is an `integer`. `multipleOf`
    allows a relative error of one part in a billion in the quotient,
    so `0.0075` is a multiple of `0.0001` although the division is not
    exact in binary floating point.
15. **A string's length counts characters, not bytes.** `minLength`
    and `maxLength` count Unicode code points, as 2020-12 section 6.3
    says.
16. **An annotation's value is a copy.** A value taken from a parsed
    document does not keep that document alive in the standard library
    today, so each annotation holds its own copy of the value the
    schema wrote, and an output stays readable after its schema is
    dropped.
17. **`scherror.kind_name` is stable across releases.** Programs quote
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
- **Vocabularies switched off by a custom meta-schema.** A `$schema`
  naming a meta-schema whose `$vocabulary` leaves out, say, the
  validation vocabulary does not stop this package asserting `minimum`.
  `$vocabulary` is read only to refuse a vocabulary nobody here
  recognises.
- **Regular expressions with Unicode property classes.** `\p{Letter}`
  and the rest are refused as `SchBadPattern`; see rule 7.
- **A microcontroller build, and a browser build.** `std.json` is
  refused on the embedded tier and has no wasm runtime.

## Related packages

- [jsonpath-nv](https://novo-lang.org/packages/jsonpath-nv) selects
  parts of a JSON document by RFC 9535. It answers which parts of a
  document you asked for; this package answers whether the document is
  what it should be. Both work over `std.json`'s value.
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
novo test tests/schcompile_tests.nv            # the compile and the registry
novo test tests/schvalidate_tests.nv           # the checks and what they say
novo test tests/schfault_tests.nv              # every fault, URI resolution, the output
novo test tests/suite_core_tests.nv            # the test suite: references and anchors
novo test tests/suite_applicator_tests.nv      # the test suite: the applicators
novo test tests/suite_validation_tests.nv      # the test suite: the validation keywords
novo test tests/suite_annotation_tests.nv      # the test suite: unevaluated*, format, content
novo test tests/suite_format_tests.nv          # the test suite: the built-in formats
bash tests/coverage.sh                         # line coverage over src/
```

The oracle is the JSON-Schema-Test-Suite, the conformance suite the
specification's authors maintain. `tools/suite.py` writes the
`suite_*_tests.nv` files from its draft2020-12 directory: 1291 cases in
45 files, with the suite's remote documents and the 2020-12
meta-schemas registered, and 401 cases for the built-in formats from
its optional format files. Python's `jsonschema` gives the suite's
answer on every one of the 1291, which the script checks. Left out:
`vocabulary.json`, which switches vocabularies off by meta-schema; the
two groups whose `pattern` uses `\p{Letter}`; and the `hostname` cases
of A-labels that are not valid IDNA.

The suite records only whether an instance was valid. The assertions
about the messages and the three locations are this package's own
claim, in `schvalidate_tests.nv` and `schfault_tests.nv`, and the ones a
reviewer should read hardest.

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
