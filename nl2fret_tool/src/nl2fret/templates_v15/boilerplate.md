# TEMPLATE: Boilerplates (Hull, Jackson and Dick; DODT)

## Base boilerplates (Hull, Jackson, Dick, Requirements Engineering, Sect. 4.8 The Language of Requirements)

"Requirement Expression = Boilerplate + Placeholder values" (Sect. 4.9). "shall" is the key word that indicates the presence of a requirement; some approaches use "shall", "should" and "may" for different priorities.

Capability (stakeholder requirement):
  The <stakeholder type> shall be able to <capability>.
  The <stakeholder type> shall be able to <capability> within <performance> of <event> while <operational condition>.
  E.g. The weapons operator shall be able to fire a missile within 3 seconds of radar sighting while in severe sea conditions.
Constraint (stakeholder requirement):
  The <stakeholder> shall not be placed in breach of <applicable law>.
  E.g. The ambulance driver shall not be placed in breach of national road regulations.
System requirement with a capacity performance:
  The <system> shall <function> not less than <quantity> <object> while <operational condition>.
  E.g. The communications system shall sustain telephone contact with not less than 10 callers while in the absence of external power.
Periodicity:
  The <system> shall <function> <object> every <performance> <units>.
  E.g. The coffee machine shall produce a hot drink every 10 seconds.

## Example boilerplates for constraint requirements (Hull, Jackson, Dick, Table 4.4)

Performance/capability:   The <system> shall be able to <function> <object> not less than <performance> times per <units>.
Performance/capability:   The <system> shall be able to <function> <object> of type <qualification> within <performance> <units>.
Performance/capacity:     The <system> shall be able to <function> not less than <quantity> <object>.
Performance/timeliness:   The <system> shall be able to <function> <object> within <performance> <units> from <event>.
Performance/periodicity:  The <system> shall be able to <function> not less than <quantity> <object> within <performance> <units>.
Interoperability/capacity: The <system> shall be able to <function> <object> composed of not less than <performance> <units> with <external entity>.
Sustainability/periodicity: The <system> shall be able to <function> <object> for <performance> <units> every <performance> <units>.
Environmental/operability: The <system> shall be able to <function> <object> while <operational condition>.
Note that there may be several ways of expressing similarly classified constraints, and that constraints may have a compound classification.

## DODT (Farfeleder, Moser, Krall, Stalhane, Zojer, Panis, IEEE DDECS 2011)

A boilerplate consists of a sequence of attributes and fixed syntax elements (FSEs). Example: "<system> shall <action>" (attributes <system>, <action>; FSE "shall"). Another example: "<user> shall be able to <action>".
It is possible to combine several boilerplates by means of simple concatenation. This allows keeping the number of required boilerplates low while at the same time having a high flexibility.
Example of a DODT requirement (Grosser et al. 2023, Table I): "While in Imaging Mode, the AOCS-GNC shall have Absolute Measurement Error (AME) of at most 100 urad (3s)." with the structure "While <state>, <system> shall have <parameter> of at most <quantity> <unit>."
