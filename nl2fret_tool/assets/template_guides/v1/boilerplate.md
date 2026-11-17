# TEMPLATE: Boilerplates (Hull, Jackson and Dick; DODT style clause set)

SPEC_STATUS: partial
SPEC_SOURCES:
- Grosser et al. 2023, "A Comparative Evaluation of Requirement Template Systems", section III and Table I (project PDF). It says:
  Boilerplates [Hull, Jackson, Dick 2005, pp. 81ff] are a set of templates for different types of requirements. Stakeholder
  requirement: "The <stakeholder type> shall be able to <capability>." System requirement: "The <system> shall <function> <object>."
  These basic forms are varied to express various constraints. All templates specify a full sentence, although sub-clauses could be
  recombined. The DODT framework presents a consolidated set of all main and sub-clauses.
  Table I example (DODT): "While in Imaging Mode, the AOCS-GNC shall have Absolute Measurement Error (AME) of at most 100 urad (3s)."
  with the structure "While <state>, <system> shall have <parameter> of at most <quantity> <unit>."
- A conference submission found by web search (PCI 2020, intelligence.csd.auth.gr; title and authors NOT checked) defines its OWN
  boilerplates, NOT those of Hull, Jackson and Dick. They are used here only as an additional source of clause shapes:
  prefix "if | unless | while <state>", prefix "if | unless <event>", main "<subject> shall [not] <action>",
  main "<subject> shall [not] be able to <action>", suffix "after | before <event>", suffix "using <entity>".
  Read through a summarising web fetch tool, not verified against the full text.
- Hull, Jackson and Dick, "Requirements Engineering" (Springer), Sect. 4.9 "Requirement Boilerplates", book pages 103 to 105 (a 3 page excerpt supplied by the user;
  edition not verified). It defines "Requirement Expression = Boilerplate + Placeholder values" and gives Table 4.4 "Example boilerplates for constraint requirements"
  (copied below) and one periodicity boilerplate from Sect. 4.8: "The <system> shall <function> <object> every <performance> <units>."
  Example from the book: "The coffee machine shall produce a hot drink every 10 seconds."
- Same book, Sect. 4.8 "The Language of Requirements", book pages 101 to 103 (a second excerpt supplied by the user; the file name carries the ISBN 978-3-319-61073-3,
  which would be the 2017 edition, NOT verified). It gives the base boilerplates, copied below.
- Farfeleder, Moser, Krall, Stalhane, Zojer, Panis, "DODT: Increasing Requirements Formalism using Domain Ontologies for Improved Embedded Systems Development",
  IEEE DDECS 2011, doi 10.1109/DDECS.2011.5783092 (4 page paper supplied by the user, read in full). It says (verified): a boilerplate consists of a sequence of
  attributes and fixed syntax elements (FSEs); example "<system> shall <action>" (attributes <system>, <action>, FSE "shall"); several boilerplates can be
  combined by simple concatenation, which keeps the number of boilerplates low and the flexibility high; "<user> shall be able to <action>" is another example;
  the tool turns "will" into "shall" and rewrites phrases such as "in case that" so that the shall based boilerplates match; a requirement with several
  sentences is split into several requirements; the matching is deliberately maximal, so a requirement may be split into too many boilerplates because removing an
  extra one costs less effort than adding a missing one. The paper does NOT list the consolidated set of main and sub-clauses.
- NOT obtained: the source of the consolidated DODT clause set mentioned by Grosser et al. 2023 (which publication holds it is unknown). Sect. 4.8 of the book shows only
  a few examples, not a complete catalog. This template is therefore still incomplete and must be reported as such.
- OPTIONAL: if the file templates/boilerplate_override.md exists, its text is appended to this specification.

## Base boilerplates of Sect. 4.8 of the book (verified)

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
The book also says "shall" marks a requirement, and some approaches use "shall", "should" and "may" for different priorities.

## Table 4.4 of the book (verified, constraint boilerplates by type of constraint)

Performance/capability:   The <system> shall be able to <function> <object> not less than <performance> times per <units>.
Performance/capability:   The <system> shall be able to <function> <object> of type <qualification> within <performance> <units>.
Performance/capacity:     The <system> shall be able to <function> not less than <quantity> <object>.
Performance/timeliness:   The <system> shall be able to <function> <object> within <performance> <units> from <event>.
Performance/periodicity:  The <system> shall be able to <function> not less than <quantity> <object> within <performance> <units>.
Interoperability/capacity: The <system> shall be able to <function> <object> composed of not less than <performance> <units> with <external entity>.
Sustainability/periodicity: The <system> shall be able to <function> <object> for <performance> <units> every <performance> <units>.
Environmental/operability: The <system> shall be able to <function> <object> while <operational condition>.
Periodicity (Sect. 4.8):  The <system> shall <function> <object> every <performance> <units>.
The book says only the parts in bold are relevant to the constraint, and that several boilerplates may express a similar constraint.

## Forms that can be used (verified or secondary, see above)

Main clauses:
  The <stakeholder type> shall be able to <capability>.
  The <system> shall <function> <object>.
  <system> shall have <parameter> of at most <quantity> <unit>.
  <subject> shall [not] <action>
  <subject> shall [not] be able to <action>
Condition prefix (comma after the prefix):
  While <state>, <main clause>
  If <state or event>, <main clause>
  Unless <state or event>, <main clause>
Suffix:
  <main clause> after <event> | before <event> | using <entity>

## Combination (DODT 2011, verified)

Boilerplates may be concatenated: a sentence can be built from several boilerplates in sequence (main clause followed by condition or constraint clauses).
The book's own examples append "within <performance> of <event>" and "while <operational condition>" to a main clause.

## Not specified here (the test bench adds NO rule)

Which prefix to use for a given situation, how to express timing and durations, and how to combine several prefixes are not known from the sources.
The choice is left to the converter.

## Format examples (generic, to show the syntax only)

"The operator shall be able to reset the counter."
"The controller shall open the inlet valve."
"While in standby mode, the unit shall have a power consumption of at most 2 W."
