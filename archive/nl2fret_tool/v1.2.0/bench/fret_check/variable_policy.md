# Variable policy (section 4.0 step 2 of the prompt document, v2)

One rule, applied identically to the reference FRETish and to every generated sentence. The rule never reads the reference when it processes a generated sentence.
It is the bench author's assumption ("추측입니다"). It was fixed before any Claude output of this run existed and is not changed afterwards.

Unit: one FRETish sentence, checked alone (monolithic) with a variable table built from that sentence only. A source set (MLV or DRONE) merges the per-sentence usage statistics of its sentences by majority usage and is checked compositionally.

Per sentence, from the semantics printed by the official FRET parser (`FretSemantics.compile`), analysed by `tools/fretexpr.py`:
- role: an identifier in the consequent of the response (right side of `=>`, or the whole response when there is no implication) is Output; every other identifier (condition, scope, until or other antecedent) is Input. The scope mode variable (`in flight mode`) is an Input boolean.
- type: used as a number (compared with a numeric literal or inside arithmetic or absReal, preReal and similar): `double` when a decimal literal is present, else `integer` (FRET does not convert `0` to `0.0`, so the type follows the literals); compared with another bare identifier: `integer`; everything else: `boolean`.
- constant: an identifier that appears only as the right side of `=` against another bare identifier (e.g. `state = ap_standby_state`) is an Internal integer with a distinct constant value.
- a sentence with a user defined function application (e.g. `obstacle(currentPosition)`) is not modelled and counts as `not_run`.
- component: the component name written in the sentence. In a set the component name is replaced by one fixed name per source (FRET accepts one system component per check).

Result values: `realizable`, `unrealizable`, `unknown` (the FRET CLI printed ERROR or UNKNOWN, or no usable JSON), `parse_error` (the official parser rejected the sentence), `not_run`.
Solver and time limit are the CLI defaults used in the previous run (`--solver kind2 --timeout 120`), not changed.

Probe (v4 smoke 2): `check.py single --type-policy double` types EVERY numeric variable as double. The default policy (`literal`) is unchanged. In the v4 smoke 20 of the 26 `unknown` results were sentences of one item with `absReal(x - y) <= 35` (integer literal) while the reference uses 35.0; whether the type is the cause is not known (추측입니다). The probe compares the two policies on the same sentences; neither policy reads the reference.
