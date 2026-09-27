#!/usr/bin/env python3
"""Write tests/suite_*_tests.nv from the JSON-Schema-Test-Suite, with
Python's jsonschema as a second opinion.

The JSON-Schema-Test-Suite is the community's conformance suite: files
of `{description, schema, tests: [{description, data, valid}]}` groups,
one file per keyword.  This script takes every required file of the
draft2020-12 directory except those listed in LEFT_OUT, with the reason
for each, and writes them as Novo test suites, four files by
vocabulary.  The remote documents the suite serves at
http://localhost:1234/ and the 2020-12 meta-schemas are written as
registry documents, so a `$ref` to them resolves without a fetch.

Every case must get the suite's answer from jsonschema's
Draft202012Validator as well, or the script stops.

Needs the `jsonschema` package.  Run from the package root:
    python3 tools/suite.py path/to/JSON-Schema-Test-Suite
The output is passed through `novo fmt`.
"""
import json
import os
import subprocess
import sys

import jsonschema
import referencing
import referencing.jsonschema
from jsonschema_specifications import REGISTRY as META

# The groups left out, by description, and why.
LEFT_OUT_GROUPS = {
    # std.regex has no Unicode property classes (README rule 7), and
    # neither has Python's re, so jsonschema cannot judge them either.
    'pattern.json: pattern with Unicode property escape requires unicode mode': 'needs \\p{...}',
    'patternProperties.json: patternProperties with Unicode property escape': 'needs \\p{...}',
}

# The files left out, and why.
LEFT_OUT = {
    # A `$schema` naming a custom meta-schema whose `$vocabulary` omits
    # the validation vocabulary; this package reads `$vocabulary` only
    # to refuse an unknown required vocabulary, and does not switch
    # vocabularies off by meta-schema.
    'vocabulary.json': 'vocabularies switched off by a custom meta-schema',
}

GROUPS = {
    'core': ['anchor.json', 'boolean_schema.json', 'defs.json', 'dynamicRef.json',
             'infinite-loop-detection.json', 'ref.json', 'refRemote.json'],
    'applicator': ['additionalProperties.json', 'allOf.json', 'anyOf.json', 'contains.json',
                   'dependentSchemas.json', 'if-then-else.json', 'items.json', 'not.json', 'oneOf.json',
                   'patternProperties.json', 'prefixItems.json', 'properties.json', 'propertyNames.json'],
    'validation': ['const.json', 'dependentRequired.json', 'enum.json', 'exclusiveMaximum.json',
                   'exclusiveMinimum.json', 'maxContains.json', 'maximum.json', 'maxItems.json',
                   'maxLength.json', 'maxProperties.json', 'minContains.json', 'minimum.json',
                   'minItems.json', 'minLength.json', 'minProperties.json', 'multipleOf.json',
                   'pattern.json', 'required.json', 'type.json', 'uniqueItems.json'],
    'annotation': ['content.json', 'default.json', 'format.json', 'unevaluatedItems.json',
                   'unevaluatedProperties.json'],
}


def nv(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '$':
            out.append('\\$')
        elif ch == '\n':
            out.append('\\n')
        elif o < 32 or o == 127:
            out.append('\\x%02x' % o)
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def compact(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def remotes(root):
    docs = []
    base = os.path.join(root, 'remotes')
    for dirpath, _, names in os.walk(base):
        rel = os.path.relpath(dirpath, base)
        if rel.split(os.sep)[0] in ('draft3', 'draft4', 'draft6', 'draft7', 'draft2019-09'):
            continue
        for name in sorted(names):
            if name.endswith('.json'):
                path = os.path.join(dirpath, name)
                uri = 'http://localhost:1234/' + os.path.relpath(path, base).replace(os.sep, '/')
                docs.append((uri, json.load(open(path))))
    docs.sort()
    for uri in ['https://json-schema.org/draft/2020-12/schema'] + [
            'https://json-schema.org/draft/2020-12/meta/' + m for m in
            ('core', 'applicator', 'unevaluated', 'validation', 'meta-data', 'format-annotation',
             'content')]:
        docs.append((uri, META.contents(uri)))
    return docs


def oracle(docs):
    registry = referencing.Registry().with_resources(
        [(uri, referencing.jsonschema.DRAFT202012.create_resource(doc)) for uri, doc in docs])
    return registry


def main():
    root = sys.argv[1]
    docs = remotes(root)
    registry = oracle(docs)
    head = [
        'use std.test',
        'use std.json',
        'use schcompile',
        'use schvalidate',
        '',
        '// The documents the suite serves at http://localhost:1234/, and the',
        '// 2020-12 meta-schemas, as one registry.',
        'fn remotes() -> SchRegistry',
        '    var r = schcompile.registry()',
        '    for (uri, text) in documents()',
        '        if let Some(d) = json.parse(text)',
        '            r = schcompile.with_document(r, uri, d)',
        '    r',
        '',
        'fn documents() -> [(Str, Str)]',
        '    [']
    for uri, doc in docs:
        head.append('        (%s, %s),' % (nv(uri), nv(compact(doc))))
    head[-1] = head[-1].rstrip(',')
    head += ['    ]', '',
             '// Compile a group\'s schema against the remotes, then check that every',
             '// instance gets the suite\'s answer from both the full validation and',
             '// the fast path.',
             'fn run(group: Str, schema: Str, cases: [(Str, Str, Bool)]) [io]',
             '    let reg = remotes()',
             '    match json.parse(schema)',
             '        None    =>',
             '            test.case(group)',
             '            test.assert(false)',
             '        Some(d) =>',
             '            match schcompile.compile_with(d, reg)',
             '                Err(f) =>',
             '                    test.case(group + ": " + f.message())',
             '                    test.assert(false)',
             '                Ok(s)  =>',
             '                    for (what, data, valid) in cases',
             '                        test.case(group + ": " + what)',
             '                        match json.parse(data)',
             '                            None    =>',
             '                                test.assert(false)',
             '                            Some(i) =>',
             '                                test.assert(schvalidate.validate(s, i).valid == valid)',
             '                                test.assert(schvalidate.is_valid(s, i) == valid)',
             '']
    total = 0
    for name, files in GROUPS.items():
        lines = ['// suite_%s_tests.nv — the JSON-Schema-Test-Suite\'s draft2020-12 files' % name,
                 '// for %s.' % ', '.join(f[:-5] for f in files),
                 '//',
                 '// Written by tools/suite.py; do not edit by hand.  Each test is one',
                 '// file of the suite; each group compiles once against the suite\'s',
                 '// remote documents, and each instance must get the suite\'s answer,',
                 '// which Python\'s jsonschema was checked to give as well.',
                 ''] + head
        count = 0
        for f in files:
            groups = json.load(open(os.path.join(root, 'tests', 'draft2020-12', f)))
            fn = 'test_' + f[:-5].replace('-', '_')
            lines += ['@test', 'fn %s() [io]' % fn]
            for g in groups:
                if f + ': ' + g['description'] in LEFT_OUT_GROUPS:
                    continue
                validator = jsonschema.Draft202012Validator(g['schema'], registry=registry)
                cases = []
                for t in g['tests']:
                    got = validator.is_valid(t['data'])
                    assert got == t['valid'], (f, g['description'], t['description'])
                    cases.append('(%s, %s, %s)' % (nv(t['description']), nv(compact(t['data'])),
                                                   'true' if t['valid'] else 'false'))
                    count += 1
                lines.append('    run(%s, %s, [%s])' % (nv(f[:-5] + ": " + g['description']),
                                                      nv(compact(g['schema'])), ', '.join(cases)))
            lines.append('')
        path = 'tests/suite_%s_tests.nv' % name
        open(path, 'w').write('\n'.join(lines))
        subprocess.run(['novo', 'fmt', path], check=True, capture_output=True)
        print('%s: %d cases -> %s' % (name, count, path))
        total += count
    print('%d cases; left out: %s; groups: %s' % (total, ', '.join(LEFT_OUT), ', '.join(LEFT_OUT_GROUPS)))
    formats(root)


# The built-in formats, whose optional suite files are written as
# vectors for `schformat.check_format`.
BUILTIN = ['date', 'time', 'date-time', 'duration', 'uuid', 'ipv4', 'ipv6', 'json-pointer',
           'relative-json-pointer', 'hostname', 'regex']


def formats(root):
    lines = ['// suite_format_tests.nv — the JSON-Schema-Test-Suite\'s optional',
             '// draft2020-12 format files for the built-in formats.',
             '//',
             '// Written by tools/suite.py; do not edit by hand.  Each case is a',
             '// string the suite says is or is not in the format; the cases whose',
             '// instance is not a string test that a format ignores other types,',
             '// which the validation suites cover, and are left out here.',
             '',
             'use std.test',
             'use schformat',
             '',
             'fn check(name: Str, cases: [(Str, Str, Bool)]) [io]',
             '    let b = schformat.builtin_formats()',
             '    for (what, text, valid) in cases',
             '        test.case(name + ": " + what)',
             '        test.assert(schformat.check_format(b, name, text) == Some(valid))',
             '']
    count = 0
    for name in BUILTIN:
        groups = json.load(open(os.path.join(root, 'tests', 'draft2020-12', 'optional', 'format', name + '.json')))
        cases = []
        for g in groups:
            for t in g['tests']:
                if isinstance(t['data'], str) and not left_out(name, t):
                    cases.append('(%s, %s, %s)' % (nv(t['description']), nv(t['data']), 'true' if t['valid'] else 'false'))
                    count += 1
        lines += ['@test', 'fn test_%s() [io]' % name.replace('-', '_'),
                  '    check(%s, [%s])' % (nv(name), ', '.join(cases)), '']
    path = 'tests/suite_format_tests.nv'
    open(path, 'w').write('\n'.join(lines))
    subprocess.run(['novo', 'fmt', path], check=True, capture_output=True)
    print('formats: %d cases -> %s' % (count, path))


# Whether a format case is left out.  An A-label, a hostname label
# starting `xn--`, is valid only when its Punycode decodes to a label
# IDNA 2008 permits (RFC 5891 section 4.2.3, RFC 5892), which needs
# IDNA's tables; the built-in `hostname` checks RFC 1123's syntax, and a
# caller that needs A-labels checked registers punycode-nv's check.
def left_out(name, t):
    return name == 'hostname' and 'xn--' in t['data'].lower() and not t['valid']


if __name__ == '__main__':
    main()
