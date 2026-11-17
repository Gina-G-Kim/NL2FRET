KEYWORD REFERENCE: timing with a duration
Keywords of this group: within, for, after
Source: sections "Timing" and "Semantics of the fields"; the text below is copied from the FRETish guide.

DURATION is a positive integer optionally followed by a time-unit,
for example 12 seconds or 5 minutes. Time units can be one of the following:
* **tick** or **ticks**
* **microsecond** or **microseconds**
* **millisecond** or **milliseconds**
* **second** or **seconds** or **sec** or **secs**
* **minute** or **minutes**
* **hour** or **hours**

**NOTE: Time units are currently ignored**: they are not checked, converted
or reasoned about by FRET. To FRET, all the units mean "time points" (or
"time steps"); e.g., 3 ticks means the same as 3 seconds, which means the
same as 3 microseconds. FRET exports verification code to analysis tools,
which are in charge of interpreting the time units. Check the user manual
under "Exporting for Analysis" for more details.

EXAMPLES
* **for:** **When** errorCondition, **the** system **shall, for** 4 **seconds, satisfy** alarmOn
* **within:** **In** landing **mode, the** the system **shall within** 2 **seconds satisfy** is_stable
* **after:** **When** input = 1, **the** integrator **shall, after** 10
  **ticks, satisfy** output=10
Formulas of FRET (sections "Semantics of the fields"):
* `the system shall within 3 ticks satisfy q`
  * Required behavior: for every trigger, (q) must hold at some point with distance 3 from the trigger (i.e., at trigger, trigger+1, ..., or trigger+3). If the interval ends sooner than trigger+3, then (q) need not hold.
  * Formula (infinite traces): (F[0,3] q)
  * Formula (finite traces): ((F[0,3] q) | (F[0,2] LAST))
* `the system shall for 3 ticks satisfy q`
  * Required behavior: for every trigger, (q) must hold at the trigger and remain true for 3 time points past the trigger (i.e., trigger, trigger+1, ..., and trigger+3), or to the end of the interval if the interval ends sooner than trigger+3.
  * Formula (infinite traces): ((G[0,3] q) | (G q))
  * Formula (finite traces): ((G[0,3] q) | (LAST V q))
* `the system shall after 3 ticks satisfy q`
  * Required behavior: for every trigger, (q) must be false at all time points with distance 3 from the trigger (i.e., trigger, trigger+1, ..., and trigger+3). Moreover, (q) must hold at the point that is at distance 3+1 from the trigger, that is, trigger+3+1, except if the end of the interval occurs earlier.
  * Formula (infinite traces): (((G[0,3] (! q)) | (G (! q))) & (F[0,4] q))
  * Formula (finite traces): (((G[0,3] (! q)) | (LAST V (! q))) & ((F[0,4] q) | (F[0,3] LAST)))
Condition with each timing (upon and whenever):
* `upon p the system shall within 3 ticks satisfy q`: ((G (((! p) & (X p)) -> (X (F[0,3] q)))) & (p -> (F[0,3] q)))
* `upon p the system shall for 3 ticks satisfy q`: ((G (((! p) & (X p)) -> (X ((G[0,3] q) | (G q))))) & (p -> ((G[0,3] q) | (G q))))
* `upon p the system shall after 3 ticks satisfy q`: ((G (((! p) & (X p)) -> (X (((G[0,3] (! q)) | (G (! q))) & (F[0,4] q))))) & (p -> (((G[0,3] (! q)) | (G (! q))) & (F[0,4] q))))
* `whenever p the system shall within 3 ticks satisfy q`: (G (p -> (F[0,3] q)))
* `whenever p the system shall for 3 ticks satisfy q`: (G (p -> ((G[0,3] q) | (G q))))
* `whenever p the system shall after 3 ticks satisfy q`: (G (p -> (((G[0,3] (! q)) | (G (! q))) & (F[0,4] q))))
