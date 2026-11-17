KEYWORD REFERENCE: timing at a time point
Keywords of this group: (timing omitted), immediately, initially, at the first timepoint, at the same timepoint, at the next timepoint, finally, at the last timepoint, eventually, always, never
Source: sections "Timing" and "Semantics of the fields"; the text below is copied from the FRETish guide.

specifies the time points or time intervals, where a response has to occur once scope and condition(s) are satisfied. Supported options are

* **immediately**, **initially**, **at the first timepoint**, **at the same timepoint** (synonyms)
* **at the next timepoint**
* **finally**, **at the last timepoint** (synonyms)
* **eventually**
* **always**
* **never**
* **within** DURATION
* **for** DURATION
* **after** DURATION
* **until** STOP_CONDITION
* **before** STOP_CONDITION

EXAMPLES
* **immediately:** **In** roll_hold **mode** RollAutopilot **shall immediately satisfy if** (roll_angle
  < 6.0 & roll_angle > -6.0) **then** roll_hold_reference = 0.0
* **next:** **When** currentOverload **the** circuitBreaker **shall,
  at the next timepoint, satisfy** shutoff
* **finally:** **In** flight **mode**, **the** vehicle **shall finally
  satisfy** landingMode_initiated
* **eventually:** **In** landingMode **the** system **shall eventually satisfy**
  LandingGearLowered
* **always:** **The** autopilot **shall always satisfy if** allGood **then**
  state = nominal
* **never:** **In** drivingMode **the** system **shall never satisfy**
  cellPhoneOn & !cellPhoneHandsFree
Formulas of FRET (sections "Semantics of the fields"):
* `the system shall satisfy q`
  * Required behavior: for every trigger, (q) must hold at some time point between (and including) the trigger and the end of the interval.
  * Formula (infinite traces): (F q)
  * Formula (finite traces): ((! LAST) U q)
* `the system shall immediately satisfy q`
  * Required behavior: for every trigger, if trigger holds then (q) also holds at the same time point.
  * Formula (infinite traces): q
  * Formula (finite traces): q
* `the system shall at the next timepoint satisfy q`
  * Required behavior: for every trigger, (q) must hold at the next time step.
  * Formula (infinite traces): (X q)
  * Formula (finite traces): (LAST | (X q))
* `the system shall finally satisfy q`
  * Required behavior: for every trigger, if trigger holds, then (q) holds at the end of the interval.
  * Formula (infinite traces): TRUE
  * Formula (finite traces): (LAST V (LAST -> q))
* `the system shall eventually satisfy q`
  * Required behavior: for every trigger, (q) must hold at some time point between (and including) the trigger and the end of the interval.
  * Formula (infinite traces): (F q)
  * Formula (finite traces): ((! LAST) U q)
* `the system shall always satisfy q`
  * Required behavior: for every trigger, (q) must hold at all time points between (and including) the trigger and the end of the interval.
  * Formula (infinite traces): (G q)
  * Formula (finite traces): (LAST V q)
* `the system shall never satisfy q`
  * Required behavior: for every trigger, (q) must be false at all time points between (and including) the trigger and the end of the interval.
  * Formula (infinite traces): (G (! q))
  * Formula (finite traces): (LAST V (! q))
Condition with each timing (upon and whenever):
* `upon p the system shall satisfy q`: ((G (((! p) & (X p)) -> (X (F q)))) & (p -> (F q)))
* `upon p the system shall immediately satisfy q`: ((G (((! p) & (X p)) -> (X q))) & (p -> q))
* `upon p the system shall at the next timepoint satisfy q`: ((G (((! p) & (X p)) -> (X (X q)))) & (p -> (X q)))
* `upon p the system shall eventually satisfy q`: ((G (((! p) & (X p)) -> (X (F q)))) & (p -> (F q)))
* `upon p the system shall always satisfy q`: ((G (((! p) & (X p)) -> (X (G q)))) & (p -> (G q)))
* `upon p the system shall never satisfy q`: ((G (((! p) & (X p)) -> (X (G (! q))))) & (p -> (G (! q))))
* `whenever p the system shall satisfy q`: (G (p -> (F q)))
* `whenever p the system shall immediately satisfy q`: (G (p -> q))
* `whenever p the system shall at the next timepoint satisfy q`: (G (p -> (X q)))
* `whenever p the system shall eventually satisfy q`: (G (p -> (F q)))
* `whenever p the system shall always satisfy q`: (G (p -> (G q)))
* `whenever p the system shall never satisfy q`: (G (p -> (G (! q))))
