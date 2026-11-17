KEYWORD REFERENCE: timing with a stop condition
Keywords of this group: until, before
Source: sections "Timing" and "Semantics of the fields"; the text below is copied from the FRETish guide.

STOP_CONDITION is a Boolean expression (see help for the Condition
field). The timing **before** means that the response must happen at least
once strictly before the STOP_CONDITION holds. The timing **until** means
that the response must hold at least until strictly before the
STOP_Condition holds.

EXAMPLES
* **until:** **In** CountdownMode **the** system **shall, until** Count = 0, **satisfy** Count > 0
* **before:** **The** system **shall, before** TakeOff, **satisfy** CheckListTasksCompleted
Formulas of FRET (sections "Semantics of the fields"):
* `the system shall until r satisfy q`
  * Required behavior: for every trigger, (q) must remain true until (but not necessarily including) the point where the stop condition holds, or to the end of the interval. If the stop condition never occurs, (q) must hold until the end of the scope, or forever. If the stop condition holds at the trigger, the requirement is satisfied.
  * Formula (infinite traces): (r V (q | r))
  * Formula (finite traces): ((r V (q | r)) | (LAST V q))
* `the system shall before r satisfy q`
  * Required behavior: for every trigger, (q) must hold at least once strictly before the state where the stop condition holds. If the stop condition never occurs in the interval, (q) does not need to hold. If the stop condition holds at the trigger, the requirement is not satisfied.
  * Formula (infinite traces): (q V (! r))
  * Formula (finite traces): ((q | LAST) V (! r))
Condition with each timing (upon and whenever):
* `upon p the system shall until r satisfy q`: ((G (((! p) & (X p)) -> (X (r V (q | r))))) & (p -> (r V (q | r))))
* `upon p the system shall before r satisfy q`: ((G (((! p) & (X p)) -> (X (q V (! r))))) & (p -> (q V (! r))))
* `whenever p the system shall until r satisfy q`: (G (p -> (r V (q | r))))
* `whenever p the system shall before r satisfy q`: (G (p -> (q V (! r))))
