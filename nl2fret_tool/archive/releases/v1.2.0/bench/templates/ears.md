# TEMPLATE: EARS (Easy Approach to Requirements Syntax)

SPEC_STATUS: verified_subset
SPEC_SOURCES:
- Grosser et al. 2023, "A Comparative Evaluation of Requirement Template Systems" (project PDF), Table I and text.
- Majumdar et al. 2011, Adv-EARS, Table 1, column "Definition in EARS" (project PDF).
- The original EARS paper (Mavin et al. 2009) was NOT read in this project. The ordering of clauses in the Complex type
  is therefore not verified.

## Sentence types and keyword syntax

1. Ubiquitous (no keyword):
   The <system name> shall <system response>
2. Event-driven:
   WHEN <optional preconditions> <trigger> the <system name> shall <system response>
3. Unwanted behaviour:
   IF <optional preconditions> <trigger>, THEN the <system name> shall <system response>
4. State-driven:
   WHILE <in a specific state> the <system name> shall <system response>
5. Optional feature:
   WHERE <feature is included> the <system name> shall <system response>
6. Complex: a combination of the keyword clauses above in one sentence.
   The order of the clauses is not verified in the sources.

## Not specified by the sources (the test bench adds NO rule here)

There is no separate slot for timing in the templates: timing words, if any, must be put somewhere in the sentence.
When a situation fits more than one keyword (WHEN, IF-THEN, WHILE), the choice is left to the converter.

## Format examples (generic, to show the syntax only)

"The pump shall keep the pressure below 5 bar."
"WHEN the start button is pressed the controller shall open the inlet valve."
"IF the sensor reports a fault, THEN the controller shall raise an alarm."
"WHILE the system is in standby the controller shall refuse new jobs."
