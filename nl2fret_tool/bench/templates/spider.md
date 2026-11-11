# TEMPLATE: SPIDER structured English (Konrad and Cheng)

SPEC_STATUS: verified
SPEC_SOURCES:
- Konrad and Cheng, "Real-time Specification Patterns", ICSE 2005, Figure 3 "Structured English grammar" (complete grammar, rules 1 to 26; PDF supplied by the user,
  read in full). The bench uses this grammar as the SPIDER structured English. Caveat: the tool named SPIDER (Autili et al.) is a later work that reuses this
  style and adds extensions (see the secondary examples). Whether SPIDER's own grammar differs in details from Figure 3 is NOT verified.
- Secondary examples: Konrad and Cheng, RE 2005 (grammar excerpt, same style); Autili et al. (extensions); Grosser et al. 2023, Table I.
- OPTIONAL: if the file templates/spider_override.md exists, its text is appended to this specification.

## Complete grammar (ICSE 2005, Figure 3). Literal terminals are in double quotes.

 1 property                    ::= scope ", " specification "."
 2 scope                       ::= "Globally" | "Before " R | "After " Q | "Between " Q " and " R | "After " Q " until " R
 3 specification               ::= qualitativeType | realtimeType
 4 qualitativeType             ::= occurrenceCategory | orderCategory
 5 occurrenceCategory          ::= absencePattern | universalityPattern | existencePattern | boundedExistencePattern
 6 absencePattern              ::= "it is never the case that " P " holds"
 7 universalityPattern         ::= "it is always the case that " P " holds"
 8 existencePattern            ::= P " eventually holds"
 9 boundedExistencePattern     ::= "transitions to states in which " P " holds occur at most twice"
10 orderCategory               ::= "it is always the case that if " P " holds" ( precedencePattern | precedenceChainPattern1-2 | precedenceChainPattern2-1 |
                                   responsePattern | responseChainPattern1-2 | responseChainPattern2-1 | constrainedChainPattern1-2 )
11 precedencePattern           ::= ", then " S " previously held"
12 precedenceChainPattern1-2   ::= " and is succeeded by " S ", then " T " previously held"
13 precedenceChainPattern2-1   ::= ", then " S " previously held and was preceded by " T
14 responsePattern             ::= ", then " S " eventually holds"
15 responseChainPattern1-2     ::= ", then " S " eventually holds and is succeeded by " T
16 responseChainPattern2-1     ::= " and is succeeded by " S ", then " T " eventually holds after " S
17 constrainedChainPattern1-2  ::= ", then " S " eventually holds and is succeeded by " T ", where " Z " does not hold between " S " and " T
18 realtimeType                ::= "it is always the case that " ( durationCategory | periodicCategory | realtimeOrderCategory )
19 durationCategory            ::= "once " P " becomes satisfied, it holds for " ( minDurationPattern | maxDurationPattern )
20 minDurationPattern          ::= "at least " c " time unit(s)"
21 maxDurationPattern          ::= "less than " c " time unit(s)"
22 periodicCategory            ::= P " holds " boundedRecurrencePattern
23 boundedRecurrencePattern    ::= "at least every " c " time unit(s)"
24 realtimeOrderCategory       ::= "if " P " holds, then " S " holds " ( boundedResponsePattern | boundedInvariancePattern )
25 boundedResponsePattern      ::= "after at most " c " time unit(s)"
26 boundedInvariancePattern    ::= "for at least " c " time unit(s)"

Notes from the paper: "precede" and "succeed" denote strict past and future; "previously held" and "eventually holds" denote non-strict past and future.
"S eventually holds" is satisfied if S holds in the current state. P, Q, R, S, T, Z are Boolean propositions. c is a time bound (integer).
A property is always one sentence "scope, specification." and the scope part is mandatory.

## Example sentences

- "Globally, it is always the case that if P holds, then S holds after at most c time unit(s)."   (rule 24 + 25)
- "Globally, it is always the case that if P holds, then S eventually holds."                      (rule 10 + 14)
- "Globally, it is always the case that P holds at least every c time unit(s)."                    (rule 22 + 23)
- "Globally, it is never the case that P holds."                                                   (rule 6)
- "Globally, P eventually holds."                                                                  (rule 8)
- Secondary (Autili et al., extensions beyond Figure 3): "After Q, it is always the case that P holds until R holds."
  and "Globally, it is always the case that if P held for T time units, then S holds."
- Secondary (Grosser et al. Table I): "Between Q and R, it is always the case that P holds."

## How to construct a sentence

P, Q, R, S, T, Z and the time bound c are NOT abstract letters in the output. Replace them by the exact text taken from the requirement
(in parentheses if they contain operators). Keep numbers and their units (write the unit given in the requirement, for example "200 secs").
The grammar has no modal verb slot and no component slot. Content such as the component name must still appear, inside a proposition.
If the grammar cannot carry some content, list it in "unmapped_content".
