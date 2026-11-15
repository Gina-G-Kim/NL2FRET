# TEMPLATE: Adv-EARS (Advanced EARS)

SPEC_STATUS: verified
SPEC_SOURCES:
- Majumdar et al. 2011, "Adv-EARS: A Formal Requirements Syntax for Derivation of Use Case Models",
  Table 1 and Section 4.1 (project PDF). The text was re-extracted with pdftotext and compared with Table 1 in an earlier session.

## Differences from EARS (from the paper)

- <entity> replaces <system name>. Entities are the nouns: external and internal actors interacting with the system.
- <functionality> replaces <system response>. Functionalities are the verbs and map to use cases.
- A new Hybrid (HY) type: event driven and conditional.
- All EARS syntaxes are extended into several alternative forms (listed below).

## Syntax by requirement type (alternatives are separated by " | ")

UB (Ubiquitous):
  The <entity> shall <functionality>
  | The <entity> shall <functionality> the <entity> for <functionality>

EV (Event-driven):
  When <optional preconditions> the <entity> shall <functionality>
  | When <optional preconditions> the <entity> shall perform <functionality>
  | When <entity> <functionality> the <entity> shall <functionality>

UW (Unwanted behaviour):
  IF <preconditions> THEN the <entity> shall <functionality>
  | IF <preconditions> THEN the <functionality> of <functionality> shall <functionality>
  | IF <preconditions> THEN the <functionality> of <functionality> shall <functionality> to <functionality>
  | IF <preconditions> THEN the <functionality> of <functionality> shall <functionality> to <functionality> and <functionality>

ST (State driven):
  WHILE <in a specific state> the <entity> shall <functionality>
  | WHILE <in a specific state> the <functionality> shall <functionality>

OP (Optional features):
  WHERE <feature is included> the <entity> shall <functionality>
  | WHERE <preconditions> the <functionality> shall <functionality>
  | WHERE <preconditions> the <functionality> of <functionality> shall <functionality> to <functionality>

HY (Hybrid, new in Adv-EARS):
  <While-in-a-specific-state> if necessary the <functionality> shall <functionality>
  | <While-in-a-specific-state> if necessary the <entity> shall perform <functionality>
  | <While-in-a-specific-state> if <preconditions> the <functionality> shall <functionality>

## Not specified by the sources (the test bench adds NO rule here)

There is no slot for timing. When a situation fits several types or alternative forms, the choice is left to the converter.
The paper's own example sentences come from an insurance case study and are not reused here.

## Format examples (generic, to show the syntax only)

"The unit shall log every restart."
"When the door is opened the alarm shall sound."
"WHILE in a standby state if the battery is low the unit shall perform a shutdown."
