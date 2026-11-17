# FRETISH SEMANTICS SUPPLEMENT (v1.4)

Every sentence below is quoted from the official FRET documentation (NASA-SW-VnV/fret repository, commit cf0f913, directory fret-electron/docs/_media/user-interface/examples/; the file is named in brackets). The test bench adds NO rule about which form fits a given natural language sentence. The supplement only states what each form means. Statements already given above in the guide are not repeated.

## Condition [condition.md]
- Official examples: "Upon powered_on the component shall immediately satisfy bootup"; "Whenever intruder the alarm shall immediately satisfy sound".
- Official contrast, "in the case where at some point p holds forever": "Upon p the software shall eventually satisfy q" and "Whenever p the software shall eventually satisfy q". "In the first, q must be satisfied at least once. In the second, q must be satisfied infinitely often."
- "Validity of each Boolean Expression BEXP can be optionally stated by writing "BEXP is true" (same as BEXP) or "BEXP is false" (same as ! BEXP)."

## Scope [scope.md]
- "or if not specified as above, then globally, i.e., throughout the entire execution."
- "The only modes mean that when the system is not in the specified relationship to the mode (i.e., the system is not in/after/before the mode) the response must not occur."
- Official examples: "(global) The system shall always satisfy count >= 0"; "In landing mode the system shall eventually satisfy decrease_speed"; "When not in initialization mode the system shall always satisfy commands_accepted".
- "It has been found to be useful to allow more general boolean expressions in place of simple mode variables. The keyword While for boolean expressions has a meaning like In for mode variables." Official example: "While mode = 4 the watch shall always satisfy alarm_icon_on".

## Timing [timing.md]
- "specifies the time points or time intervals, where a response has to occur once scope and condition(s) are satisfied."
- "immediately, initially, at the first timepoint, at the same timepoint (synonyms)"; "finally, at the last timepoint (synonyms)".
- "The timing before means that the response must happen at least once strictly before the STOP_CONDITION holds. The timing until means that the response must hold at least until strictly before the STOP_Condition holds."
- "NOTE: Time units are currently ignored: they are not checked, converted or reasoned about by FRET. To FRET, all the units mean "time points" (or "time steps")".
- Official examples: "The autopilot shall always satisfy if allGood then state = nominal"; "In landingMode the system shall eventually satisfy LandingGearLowered"; "In drivingMode the system shall never satisfy cellPhoneOn & !cellPhoneHandsFree"; "When currentOverload the circuitBreaker shall, at the next timepoint, satisfy shutoff"; "When errorCondition, the system shall, for 4 seconds, satisfy alarmOn".

## Values at the previous time point [temporal_condition_explanations.md]
- "There are three operators that return the value of an expression at the previous time point. FRET only formalizes them in past-time. The operators are preBool(initBool,p), preInt(initInt,n) and preReal(initReal,x)."
- "If the operator is evaluated at the start of the trace, where there is no previous time point, the value of the first argument is returned."
