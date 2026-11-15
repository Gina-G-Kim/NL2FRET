# TEMPLATE: MASTeR (SOPHIST requirement templates)

SPEC_STATUS: verified_subset
SPEC_SOURCES:
- SOPHIST GmbH, "Die SOPHISTen: Schablonen fuer alle Faelle", 6th edition 2024 (MASTeR brochure),
  https://sophist.de/wp-content/uploads/2025/03/MASTeR-Broschuere-6-Auflage.pdf
  Read through a summarising web fetch tool, so only template skeletons were obtained, not the full text.
- Grosser et al. 2023, "A Comparative Evaluation of Requirement Template Systems", Table I, for example phrasing.
- The exact English wording of the Property, Environment and Process templates is only known through the German
  skeleton. The English slot names below are a translation by the test bench author.
- OPTIONAL: if the file templates/masteR_override.md exists, its text is appended to this specification (use it to put in
  the exact brochure wording).

## Forms

Liability words: SHALL (mandatory), SHOULD (stakeholder wish), WILL (intended future function).

1. FunctionalMASTER, basic form
   <subject matter> SHALL <independent system activity: verb> <object>
   i.e. "The <system> shall <process verb> <object>"
2. FunctionalMASTER, user interaction
   <subject matter> SHALL PROVIDE <whom?> WITH THE ABILITY TO <verb> <object>
3. FunctionalMASTER, interface requirement
   <subject matter> SHALL BE ABLE TO <verb> <object>
4. Conditional form: the condition clause comes first, then the liability word and the subject matter.
   <condition>, <subject matter> SHALL ...
5. Detailed template: optional attributes before and after the object and optional adverbials
   (when? where? whither? whence?) before the verb.

## Condition templates (separate sub-templates, brochure chapter 4)

The condition is a subordinate clause. Three kinds, as the brochure defines them:
- LogicMASTER, keyword IF: "IF <logical statement>" or "IF <value> IS <comparison expression>". Present tense recommended.
- EventMASTER, keyword AS SOON AS: "AS SOON AS <event>" or "AS SOON AS the event <event> occurs". Perfect tense recommended.
- TimePeriodMASTER, keyword AS LONG AS: "AS LONG AS <time period>" or "AS LONG AS <system> is in the state <state>".

## Non-functional templates (brochure chapter 3; German skeletons verified, English slot names translated)

- PropertyMASTER: [<condition>] SHALL/SHOULD/WILL <subject matter> <property> [<comparison expression>] <value> <verb>
- EnvironmentMASTER: <environmental influence> <value> [<comparison expression>] [<condition>] SHALL/SHOULD/WILL <subject matter> <verb group>
- ProcessMASTER: [<condition>] SHALL/SHOULD/WILL <actor> <object> <verb>

## Not specified by the sources (the test bench adds NO rule here)

Which condition keyword to use when a situation could be read as a logical statement, an event or a time period is left to the converter.
How to combine several conditions is not specified beyond "the condition clause comes first".

## Format examples (generic, to show the syntax only)

"AS SOON AS the cover has been opened, the controller SHALL stop the motor."
"IF the supply voltage is below 10 V, the controller SHALL switch to battery operation."
"AS LONG AS the system is in the state maintenance, the controller SHALL ignore remote commands."
