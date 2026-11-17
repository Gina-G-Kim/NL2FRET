KEYWORD REFERENCE: condition keyword
Keywords of this group: upon, when, where, if, whenever, unless
Source: sections "Condition" and "Semantics of the fields"; the text below is copied from the FRETish guide.

specifies the condition after which the response shall hold,
taking into account scope and timing. A condition can be either:

* a _regular_ condition, meaning the requirement holds **_upon_** a condition becoming true; i.e., at the point
where the condition becomes true after being false, or the
condition is true at the beginning of a scope interval;

* a _holding_ condition, meaning the response holds **_whenever_** the condition holds.

A holding condition is introduced by the keyword **whenever**.
A regular condition is introduced by the keyword **upon** (or **when**,
**where**, **if**).
#### EXAMPLES

* **Upon** powered_on the component shall immediately satisfy bootup
* **Whenever** intruder the alarm shall immediately satisfy sound

The contrast between regular and holding conditions is shown in the following two
examples, in the case where at some point p holds forever:

* Upon p the software shall eventually satisfy q
* Whenever p the software shall eventually satisfy q

In the first, q must be satisfied at least once.
In the second, q must be satisfied infinitely often.

Formulas of FRET (sections "Semantics of the fields"):
* `upon p the system shall always satisfy q`
  * Trigger: first point in the interval if (p) is true and any point in the interval where (p) becomes true (from false).
  * Formula (infinite traces): ((G (((! p) & (X p)) -> (X (G q)))) & (p -> (G q)))
* `whenever p the system shall always satisfy q`
  * Trigger: every point in the interval where (p) is true.
  * Formula (infinite traces): (G (p -> (G q)))
* `unless p the system shall always satisfy q`
  * Trigger: first point in the interval if (! (p)) is true and any point in the interval where (! (p)) becomes true (from false).
  * Formula (infinite traces): ((G ((p & (X (! p))) -> (X (G q)))) & ((! p) -> (G q)))
Condition with each timing (upon and whenever):
* `upon p the system shall satisfy q`: ((G (((! p) & (X p)) -> (X (F q)))) & (p -> (F q)))
* `upon p the system shall immediately satisfy q`: ((G (((! p) & (X p)) -> (X q))) & (p -> q))
* `upon p the system shall eventually satisfy q`: ((G (((! p) & (X p)) -> (X (F q)))) & (p -> (F q)))
* `upon p the system shall always satisfy q`: ((G (((! p) & (X p)) -> (X (G q)))) & (p -> (G q)))
* `whenever p the system shall satisfy q`: (G (p -> (F q)))
* `whenever p the system shall immediately satisfy q`: (G (p -> q))
* `whenever p the system shall eventually satisfy q`: (G (p -> (F q)))
* `whenever p the system shall always satisfy q`: (G (p -> (G q)))
