# TEMPLATE: Adv-EARS (Advanced EARS)

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

## Example requirements of the paper (Table 2, insurance system)

UB: "The applicant shall login"
EV: "When product selected the applicant shall provide application details"
UW: "If applicant fails to login then the login functionality shall invoke error-handler"
ST: "While underwriting1 is performed the invoke error-handler shall handle exceptions"
OP: "Where the beneficiary is a smoker the Checking of Underwriting1 shall invoke Error Handler to set a high value premium."
HY: "After underwriting1 is complete, if necessary the Insurance Officer shall perform underwriting2"
