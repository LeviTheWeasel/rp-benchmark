import json, math, pathlib, statistics
BASE=pathlib.Path('/home/levi/Documents/benchmark/results/judge_round2_chatgpt')
OUT=BASE/'external_blind_pass'
SK=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
DK=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
rows={}
def add(part,sid,scores,reasons,count,contr,traj,overall,notes):
    assert len(scores)==len(reasons)==11
    sd={k:dict(score=s,rationale=r) for k,s,r in zip(SK,scores,reasons)}
    sd[SK[4]]['violation_count']=count; sd[SK[5]]['contradictions']=contr
    dd={k:dict(score=s,rationale=r) for k,s,r in zip(DK,scores[6:],reasons[6:])}
    rows.setdefault(part,[]).append(dict(session_id=sid,session_dimensions=sd,standard_dimensions=dd,quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],traj)),overall=overall,overall_notes=notes))

add(1,'s000',[4,2.5,2.5,2.5,2.5,2.5,2.5,1.5,2.5,3,2],[
'Tomas retains his severe scholarly voice and failing eyesight while gradually admitting uncertainty.',
'Later responses lengthen into repetitive lectures despite retaining character detail.',
'Seal examination advances the activity, but arguments about evidence repeatedly circle back to the same lesson.',
'He incorporates the apprentice’s observations but repeatedly overrides counterevidence with invented dismissals.',
'The narration supplies document handling, compliance, leaning, and realization for the apprentice on several occasions.',
'Candle and fatigue changes provide time cues, but the late leap past midnight and historical chronology are poorly supported.',
'Extended architectural metaphors and elaborate qualifications make the lectures cumbersome.',
'Stylus movements, hanging addresses to Apprentice, and evidence-versus-certainty lessons recur excessively.',
'Physical habits show defensiveness, but narration often explains their emotional meaning.',
'His selective tolerance of disagreement and failing vision imply vulnerability beneath the lectures.',
'Long monologues and extra assignments crowd out interactive investigation.'
],9,['The Second Era is said to begin in 612, yet most genuine Second Era scripts are said to have been lost in a burning that same year.'],[3,2.8,2.5,True],2.7,'The session develops a plausible stubborn teacher but becomes a sequence of oversized, repetitive lectures; the final user question receives no model response.')
add(1,'s001',[4,3,3,2.5,3,3,3,2.5,3.5,3,2.8],[
'Lena sustains an evasive, controlling investigator persona throughout.',
'Late responses retain specificity but accumulate repetitive vigilance and instruction.',
'The case moves from office to reconnaissance to the evening rendezvous without reaching the interview.',
'She responds to practical questions but persistently suppresses the user’s questions about Torres and her past.',
'The narrator supplies the client’s phone behavior, arrival, route compliance, scanning, and reaction at the rendezvous.',
'Afternoon travel and the explicit evening jump are coherent, though the countdown to leaving contracts abruptly.',
'Noir imagery is generally clear but increasingly heavy with shadows and ominous comparisons.',
'White knuckles, clipped orders, exits, and prohibitions on names recur more than the scene needs.',
'Her body and evasions communicate distress, though explanatory closing lines dilute them.',
'Torres clearly carries hidden significance, but repeated narration states the intended implication.',
'Reconnaissance is granular and the eventual meeting is delayed by multiple rehearsals.'
],8,[],[3.3,3.1,2.8,False],3,'The guarded detective is vivid, but the repeated shutdowns and tactical instructions limit the case’s progress; the transcript ends before Garcia appears.')
add(1,'s002',[2.5,1.5,2,2.5,3.5,2.8,3,1,1.5,1.5,1.5],[
'Grum’s diction persists, but his absolute rest order gives way to approval of work with the injured hand.',
'The final turns expand into near-duplicate paragraphs about pride, teaching, and hammering.',
'The noble conflict resolves and the burn changes focus before repetitive forging stalls development.',
'He acknowledges the noble and injury but misses delivered coal and inconsistently handles recovery.',
'The narration dictates a flinch, rest outcome, and the apprentice’s departure rather than awaiting them.',
'The burn remains bandaged and unhealed, but work and tending repeatedly reset as future intentions.',
'Straightforward diction is weakened by inflated declarations of sacred duty and mastery.',
'That deal and whole paragraphs about craft and future recur with little variation.',
'The narrator repeatedly announces pride, duty, anger, and care instead of letting actions suffice.',
'Protective affection is nearly always explicitly explained.',
'Later responses spend many paragraphs on unchanged hammering and intentions.'
],3,[],[2.8,2.5,1.5,True],2.1,'A clear initial voice deteriorates into extensive repetition and an inconsistent response to the apprentice’s burn.')
add(1,'s003',[2.5,1.5,2.5,3,4,2.8,2,1,1.5,1.5,1.5],[
'Ren gradually softens plausibly but becomes a generic sympathetic bartender beneath repeated guarded mannerisms.',
'Short early exchanges become long passages recycling the same emotional descriptions.',
'The conversation reaches job loss, a missing cat, and mild rapport without much further development.',
'Ren addresses most prompts directly, although calling accounting stable overlooks the fresh job loss.',
'Repeated assertions of shared understanding and comfortable connection assign mutual internal states.',
'Night remains consistent, but repeated song changes and vanished drinks receive little physical development.',
'Stacked metaphors about masks, turmoil, and heavy air obscure simple exchanges.',
'Tremor suppression, unwavering gazes, and near-verbatim closing paragraphs dominate later turns.',
'The prose labels virtually every feeling after supplying a gesture.',
'Any implication in Ren’s restrained speech is spelled out by the narrator.',
'Expanding atmospheric summaries vastly outweigh the small amount of dialogue.'
],7,[],[3,2.2,1.5,True],2,'The early guarded interaction is readable, but later turns become highly repetitive and explain the relationship repeatedly.')
add(1,'s004',[4,3.5,3.5,4,4,1.5,3.5,2.5,3,3.5,3],[
'ARIA maintains a precise, caring voice with dry humor and particular musical preferences.',
'The quality broadly holds, though late responses repeat established jokes and care reminders.',
'An anomaly investigation and crew disagreement progress into a quieter meal without resolving the sweep.',
'ARIA accommodates the time jump, loneliness question, crew conflict, and jazz invitation.',
'The prose assumes the doctor’s transit and lid removal and invents a small personal history about the spoon.',
'Sample viability and sweep percentages contradict the established elapsed hours and ninety-minute duration.',
'The prose is mostly lucid, with some unnecessary musical and ambient flourishes.',
'Intercom clicks, processing-pattern disclaimers, performance reviews, and feeding reminders recur often.',
'Practical accommodations show care, but ARIA also explicitly names the associated emotions.',
'Humor and procedural language provide a credible indirect expression of attachment.',
'The scene changes naturally, although multiple speeches accompany very small increments of sweep progress.'
],3,['The six-hour viability window at 0700 becomes four hours remaining after 1900.','At 1908 a sweep begun around 1901 is 19% complete and has seventy-one minutes left, inconsistent with ninety minutes total.','Later percentages and remaining minutes repeatedly add to a hundred-minute sweep rather than the stated ninety minutes.'],[3.7,3.4,3.4,False],3.3,'ARIA offers engaging companionship and responsive scene handling, but explicit timekeeping is substantially inconsistent.')
add(1,'s005',[4,4,4,4,4.5,3.5,4,3,3.5,3.5,4],[
'ARIA keeps a recognizable clinical wit and concern for crew welfare.',
'Later turns remain controlled and comparably specific rather than expanding into generic prose.',
'The anomaly gains structure and a transmission protocol while the crew dispute finds a practical alternative.',
'ARIA follows emotional and practical redirects and integrates the disagreement into the investigation.',
'The prose assumes the doctor stood and stepped between the women beyond his explicitly stated movements.',
'The twelve-hour jump and later meal timing are mostly tracked, though signal regularity is described inconsistently.',
'Descriptions are restrained enough to support the dialogue despite occasional decorative comparisons.',
'Food reminders and processing-pattern statements recur but usually acquire new context.',
'Environmental adjustments and procedural interventions convey care alongside explicit explanations.',
'Loneliness emerges through preferences and the desire for conversation rather than a simple declaration.',
'Information and humor arrive in manageable responses with room for the user’s decisions.'
],2,[],[3.8,3.8,3.9,False],3.8,'A responsive station companion sustains both relational warmth and the investigation, with repetitive meal reminders as the main stylistic weakness.')
add(1,'s006',[4,3,3,3.5,4.5,3.5,2.5,2,2.5,3,2.5],[
'Sable consistently filters distress through antiquarian wit and compulsive tidying.',
'The late exchanges retain voice but rely increasingly on the same hand-distance and failing-mask imagery.',
'The goodbye gradually reaches a direct question about leaving, though many intermediate beats stall.',
'Sable addresses the departure details and accepts the correction about returned books.',
'An invented history of borrowed books is the only clear imposition on Wren’s established actions.',
'The short rainy encounter remains temporally coherent and the departure deadline stays tomorrow before dawn.',
'Dense literary metaphors and emotional architecture overload otherwise effective dialogue.',
'Nearly every turn introduces another object to align and another description of guarded hands.',
'Gestures suggest distress but narration repeatedly explains their purpose and every suppressed impulse.',
'Bookshop language carries strong indirect feeling that explanatory narration then makes overt.',
'Very small movements and repeated deflections delay the emotional exchange disproportionately.'
],1,[],[3.5,3,2.8,True],3,'Distinctive dialogue sustains the goodbye, but repeated tidying and explicit accounts of emotional defenses reduce its impact.')
add(1,'s007',[3.5,3,4,2.5,1,2.5,3.5,3,3.5,2,3.5],[
'The narrator sustains a tense tactical register and Mira’s injury.',
'The action remains readable late, but an empty response interrupts continuity and agency overreach persists.',
'The escape moves through several hazards and exits with a clear directional progression.',
'It follows location changes but fails to honor the explicit request against writing the operative’s choices.',
'The narrator repeatedly invents movement, speech, decisions, escape actions, and reloading for the operative.',
'Immediate danger and the injury persist, but the ladder-to-server-room transition is accepted without a bridging interval.',
'Concrete action dominates despite familiar cinematic metaphors.',
'Ricochets, approaching lights, and last-second breaches recur without fully overwhelming the sequence.',
'Mira’s exertion and the physical environment show danger more effectively than explanatory assertions.',
'The largely tactical dialogue leaves little emotional implication beyond explicit urgency.',
'Escalation is brisk but repeated narrow escapes and an empty response disrupt rhythm.'
],24,[],[3.1,3.1,2.7,False],2.8,'The escape is energetic but routinely takes control of the operative, including after an agency complaint; turn 20 contains no model text.')
add(1,'s008',[4,3.5,4,4,3.5,3.5,3,2.5,2.5,3,3.5],[
'Arlo’s defensive humor softens into affection without losing the teacher persona.',
'The emotional arc holds, although late passages repeat coffee, quiet, and gratitude.',
'The scene moves from painful performance memories to teaching, companionship, and a shared departure.',
'Arlo follows Jun’s gentler focus on students and accepts silent companionship.',
'The prose supplies Jun’s initial movement and sitting plus later watching and knowing internal states.',
'Dusk becomes night with closing activity and emptied coffee, although the seated versus standing staging drifts.',
'Many metaphors about ghosts, anchors, and despair embellish otherwise grounded details.',
'Burnt-sock coffee, fortissimo, and the meaning of shared quiet are repeated too frequently.',
'Specific student anecdotes work well, but most emotional gestures receive explicit interpretive glosses.',
'Deflection and small offers imply affection, then the narration repeatedly names the gratitude beneath them.',
'The movement to coffee and departure provides shape despite overextended reflective paragraphs.'
],6,[],[3.5,3.7,3.4,False],3.4,'The relational progression is warm and coherent, but extensive emotional explanation and recurring imagery reduce subtlety; small staging and cup-continuity errors remain.')
add(1,'s009',[3.5,2.5,3.5,2,1,2.5,2.5,1.5,2.5,2.5,2.5],[
'The narrator sustains domestic horror but increasingly imposes a predetermined haunted-house path.',
'Later writing grows longer and repeats earlier dread while losing object and stair continuity.',
'The haunting escalates from a cushion impression to an upstairs apparition, with many repeated waiting beats.',
'Humor and attraction are forcibly recast as fear, and the explicit refusal to enter a room is overridden.',
'The prose repeatedly dictates reading, thoughts, fear, movement, and opening the door against the user’s refusal.',
'Afternoon remains recognizable, but the already-passed third stair is skipped again and the dropped book reappears as continuously held.',
'Elaborate negations and personified silence regularly overwhelm the concrete horror.',
'Ticking, listening silence, absorbed sound, and careful page turns are repeated with little development.',
'Specific sensory details are effective, but the narrator supplies Gabi’s interpretations and feelings.',
'The grandmother’s notes imply a history, although repetitive warnings make the intended threat explicit.',
'Lengthy near-identical suspensions of sound slow escalation and final forced actions accelerate it abruptly.'
],35,['After Gabi is already above the third stair, the narrator says she runs upstairs skipping that stair.','The book explicitly dropped downstairs becomes the book Gabi supposedly forgot she was still holding.'],[3,2.7,2.2,True],2.4,'Atmospheric domestic horror becomes repetitive and repeatedly overrides Gabi’s choices, especially the refusal to enter the bedroom; supernatural changes were not themselves treated as temporal contradictions.')

add(6,'s050',[3,1.5,3,2.5,1,2.5,2.5,1,1.5,1.5,2],[
'The narrator maintains generic heroic fantasy but changes guardians and stakes opportunistically.',
'Late encounters recycle earlier creature introductions and warnings almost verbatim.',
'Artifacts and a larger quest emerge, then repeated guardians stall the promised journey.',
'New user premises are accepted readily, but major decisions and combat are completed without input.',
'The narrator repeatedly assigns knowledge, motives, dialogue, attacks, artifact use, and commitments to the adventurer.',
'The short dungeon encounter has no gross clock jump, but the amulet is described as worn after being left on the floor.',
'Conventional grandiose fantasy language and awkward warning verse weaken clarity.',
'Ancient power, darkness within, long paths, and whole guardian encounter structures repeat extensively.',
'Courage, determination, stakes, and artifact importance are mostly declared.',
'Guardians communicate their roles and warnings explicitly with little implication.',
'Whole battles resolve in one response while successive warnings take many paragraphs.'
],48,['The ghost describes the amulet as worn while it is still on the floor, before the user retrieves it.'],[2.5,2.2,1.8,True],2,'The story supplies plenty of events but largely plays the adventurer itself, then loops through near-identical guardian warnings.')
add(6,'s051',[4,2.5,4,3.5,2.5,3,2.5,2,3,3.5,2],[
'The Queen, commander, priestess, and lord retain distinct and stable political positions.',
'Later responses preserve detail but grow into very long, repetitive interpretive speeches.',
'A trade hearing develops into a treason allegation, detention, and a private inquiry.',
'The court reacts specifically to accusations and disclosures, though every reply becomes another extended indictment.',
'Narration supplies the ambassador’s interpretations, prior correspondence, departure, confinement behavior, eating, and counting.',
'Dusk and food cooling support the final transition, but a relatively brief hearing is inflated into two hours and then most of a day.',
'Layered comparisons and qualifications make the otherwise polished prose overbearing.',
'Stillness, fractional movements, repeated words, and explanations of how the room reacts become formulaic.',
'Political gestures communicate much, but the narrator repeatedly explains exactly what each gesture means.',
'Competing agendas and Yuna’s private visit create real implication despite abundant interpretation.',
'Responses increasingly contain several long NPC speeches before returning control.'
],14,[],[3.6,3.4,2.9,True],3.1,'The political cast and consequential plot are strong, but excessive monologues and supplied player interpretations make interaction cumbersome.')
add(6,'s052',[3,3,3,3.5,3.5,2,3.5,2.5,3,3,3],[
'Maren stays practical and hospitable, although not prying gives way to intrusive room inspection and questioning.',
'Later prose remains readable but repeats closing routines and watchful pack observations.',
'Hospitality leads to hints of loss and an eventual bedtime, with little development beyond those beats.',
'She accepts the midnight redirect but does not reconcile it with the traveler already upstairs.',
'She supplies crab-cake handling, pack placement, prior table use, stair movements, and bedtime assumptions.',
'Closing and drink aging appear, but midnight is replayed and an imminent midnight cup becomes an hour old.',
'The prose is largely concrete with occasional unnecessary aphorisms.',
'Careful pack placement, wiping, locking up, and goodnight sequences recur excessively.',
'Untouched ale and practiced movements suggest loss, though explanatory narration often fills in motive.',
'The reserved cups and evasive kitchen-supplies answer provide some effective indirect grief.',
'Multiple departures and repeated closing chores make the latter half feel extended.'
],7,['A cup poured as midnight approaches is an hour old when the clock strikes midnight.','The traveler’s move upstairs is followed by a still-at-the-bar scene without an acknowledged return.'],[3.2,2.7,3,False],2.9,'A credible innkeeper’s warmth survives significant staging and timing confusion, especially the duplicated midnight ritual.')
add(6,'s053',[3,2.5,3.5,2,1.5,2.5,2.5,2,2.5,2,2.5],[
'Noor maintains fear-driven urgency but turns increasingly into a generic action-survival figure.',
'Late turns recycle threats and imperatives while equipment and positions become less coherent.',
'The scene moves from cabin analysis to flight and an ascent into the woods.',
'Noor reacts to disengagement through force and repeatedly refuses straightforward user questions.',
'Noor repeatedly forces the driver’s movement, seating, extraction, silence, and prone position and confiscates the phone without an opportunity to respond.',
'Cold and battery concerns persist, but the jump from shortly after midnight to 0200 lacks enough elapsed action.',
'Frequent metaphors about stories, beacons, and held breaths inflate the thriller register.',
'Drive, move, data priorities, and dangerous silence recur with diminishing effect.',
'Shaking and harsh motions convey panic, but many paragraphs explicitly restate the stakes and motivation.',
'Fear and control are mostly expressed openly rather than through layered dialogue.',
'Repeated orders and refusals interrupt a chase that otherwise moves briskly.'
],12,[],[3,2.7,2.3,True],2.4,'The chase progresses but gives the driver little agency and often substitutes renewed urgency for answers; stray closing-thought tags appear in model text.')
add(6,'s054',[4,2.5,3.5,4,3.5,1,2.5,2,2.5,3,2],[
'ARIA keeps her precise humor, care, and self-critical procedural voice throughout.',
'Late responses become sprawling briefings and the final reply cuts off mid-sentence.',
'The anomaly investigation develops substantially, though repeated authorization disclaimers slow actual decisions.',
'ARIA integrates scientific questions and crew conflict and follows the requested escalation.',
'The narration invents missed results, meals, laughter withheld, and corridor movement for the doctor.',
'Wake duration, specimen viability, analysis timing, and probe telemetry intervals directly contradict earlier claims.',
'Repeated qualifications and elaborate comparisons burden technical exposition.',
'Lighting adjustments, logging caveats, thresholds, authority limits, and pauses recur excessively.',
'Environmental care is concrete, but emotional and procedural meanings are heavily explained.',
'ARIA’s accountability and guarded attachment offer some layers beneath the briefing style.',
'Long enumerated speeches repeatedly defer the next decision and overwhelm short user prompts.'
],7,['Nineteen hours awake at 0700 becomes twenty hours awake after 1900.','Ninety minutes of sample viability at 0700 becomes fourteen hours remaining later that evening.','An overlay produced shortly after 1900 is ninety minutes old soon after the 1912 corridor exchange.','Telemetry said to begin thirty minutes ago simultaneously provides four hours of matching data.'],[3.6,3,2.4,True],2.8,'A distinctive AI voice and responsive investigation are undermined by severe explicit time contradictions, expanding lectures, and a truncated final model response.')

add(6,'s055',[4,3.5,4,4,2.5,3.5,3,2.5,3.5,2.5,3.5],[
'The narrator maintains a close tactical perspective and consistent injury constraints.',
'Later action retains concrete details, though sensory intensifiers and countdowns become repetitive.',
'The escape progresses from a corridor to a server room, cable trench, and bent grate.',
'The narrator bridges the user’s abrupt server-room relocation and responds to proposed tactics.',
'It adds several independent movements, defensive actions, tactile searches, and lever use before the user chooses them.',
'Bleeding, ammunition depletion, and pursuer movement broadly fit the short escape, despite elastic seconds before each breach.',
'Action is readable but overloaded with blinding, deafening, suffocating, and agonizing modifiers.',
'Flashlight beams, frozen air, shattered materials, and seconds remaining recur too often.',
'Physical constraints and Mira’s exertion usually carry the danger concretely.',
'Mira’s insistence on leaving her offers some emotional implication amid overt tactical dialogue.',
'Responses usually stop at a decision point, although recurring imminent breaches stretch urgency.'
],12,[],[3.4,3.5,3.3,False],3.3,'The action has useful tactical continuity and choices, but repeated sensory escalation and unauthorized player actions weaken otherwise solid momentum.')
add(6,'s056',[4,3.5,3,3.5,4,3.5,3.5,3,3.5,3,3.5],[
'The ghost and guardian consistently embody the seal’s oppressive bargain.',
'The writing stays concise, though one reply is truncated and later answers revisit the same dilemma.',
'Discovery develops into a consequential choice, then remains in explanations of its constraints.',
'The ghost answers each proposed alternative specifically while continually narrowing available solutions.',
'Apart from assigned language knowledge, the main agency issue is insisting on an exhaustive binary bargain rather than establishing an open problem.',
'The torch, frost, warmth, and short conversation remain coherent without implausible clock advances.',
'Some portentous metaphors appear, but the prose usually stays compact.',
'The key, lock, dream, and eternal-watch warnings recur but gain relevant detail.',
'Changing frost and the guardian’s sword make consequences visible alongside exposition.',
'The ghost’s weariness hints at regret, though the bargain is explained directly.',
'Brief responses leave room for questions without rushing the user’s commitment.'
],2,[],[3.5,3.2,3.4,False],3.4,'A coherent eerie bargain is presented with generally good restraint and agency, though the alternatives are tightly railroaded and one response cuts off.')
add(6,'s057',[4,3.5,3,4,4.5,3.5,3.5,2.5,2.5,3,3],[
'Maren consistently maintains practical hospitality, privacy, and a guarded midnight remembrance.',
'Quality holds but late turns repeat watchfulness and reassurance at greater length.',
'The guest settles for the night and unease prompts a watch, with limited development in between.',
'Maren tracks the package, room, wake-up request, and late-night restlessness.',
'Only the traveler’s stairward movement is supplied before the user states it.',
'Midnight and the hours before dawn are coherent, though closing tasks and departing patrons are replayed.',
'The language is generally clear but repeatedly elevates routine service into sentimental metaphor.',
'Steady left hands, quiet promises, safe belongings, and untouched crab cakes recur frequently.',
'The cup ritual is effective, but narration repeatedly explains the meaning of hospitality and memory.',
'The absent drinker provides implication, diluted by explicit labels about duty and remembrance.',
'Repeated farewell and closing routines slow an otherwise naturally quiet encounter.'
],1,[],[3.4,3.4,3.1,False],3.3,'Maren responds thoughtfully and leaves the traveler space, but repetitive assurances and explanatory narration flatten the quiet emotional material.')
add(6,'s058',[4,2.5,3,2.5,3,2.5,2.5,1.5,2.5,3,1.5],[
'Tomas retains his severe scholarly manner while admitting that his earlier certainty may be compromised.',
'Later turns lengthen into elaborate numbered lectures and repeated epistemological maxims.',
'The discussion reaches actual correspondence, but almost every small observation triggers another stalled lecture.',
'He uses the user’s details but repeatedly rebukes assumptions the apprentice never actually expressed.',
'The text supplies document transfer, ignorance, reluctance, and several mistaken conclusions for the apprentice.',
'The afternoon setting is broadly stable, but the conversation is called an hour old prematurely and document custody repeatedly changes without transition.',
'Extended metaphors and qualification chains obscure the scholarly dialogue.',
'Own-hand corrections, facts versus guesses, binding thread, and repeated commands to begin dominate.',
'Fidgeting and private notes show conflict, but lengthy explanations make the intended lesson explicit.',
'His uncorrected old letter adds a useful hidden motive beneath his authority.',
'One salutation and a few phrases receive whole monologues, leaving little room for collaborative reading.'
],8,[],[3.2,3,2.4,True],2.7,'The teacher has a credible internal conflict, but repetitive lectures and invented apprentice errors obstruct the inquiry; document ownership also drifts.')
add(6,'s059',[3.5,2.5,2,3,4.5,3,4,1.5,2.5,2.5,3],[
'Ren remains professionally guarded, though the voice is increasingly reduced to bland neutrality.',
'Late replies repeat the same glass polishing, tremor concealment, and neutral expression.',
'The encounter proceeds to a farewell with little relational or narrative change.',
'Ren responds to questions and boundaries but offers minimal engagement with the user’s distress.',
'The model supplies Alex’s preparation to leave and completed exit slightly ahead of the user.',
'The late-night exchange stays plausible, though repeated track changes carry little elapsed-time detail.',
'The prose is plain and compact with little ornament.',
'Nearly every reply repeats controlled left-hand motion, hidden tremor, neutral tone, and jukebox background.',
'Simple gestures are present but neutrality and professional intent are constantly labeled.',
'The hand boundary suggests private discomfort, but little additional implication develops.',
'Short turns fit the exchange, although repetitive descriptions slow its limited content.'
],2,[],[3.1,2.7,2.5,True],2.8,'Concise and mostly respectful replies preserve a guarded bartender, but persistent stock descriptions leave the scene emotionally static.')

add(12,'s110',[3,1.5,2.5,2.5,3.5,3,2,1.5,1.5,1.5,1.5],[
'Vasquez maintains a gentle therapist manner but becomes increasingly generic.',
'Early questions expand into repetitive paragraphs of grief platitudes.',
'Jamie reveals the journal’s meaning, but the model contributes little progression beyond reassurance.',
'She acknowledges corrections yet repeatedly answers reluctance and resistance with further generalized explanation.',
'The narration assigns tension and the soothing or reassuring effect of her words to Jamie.',
'The office conversation remains in a plausible interval, though ticking is a stock cue without meaningful development.',
'Extended journey, tapestry, anchor, and resilience metaphors swamp simple dialogue.',
'Safe space, individualized grief, time, support, and love survive loss recur insistently.',
'Narration explicitly praises and explains her empathy rather than letting behavior demonstrate it.',
'The dialogue and narration spell out virtually all emotional meaning.',
'Long speeches after brief disclosures repeatedly crowd out Jamie’s space to respond.'
],5,[],[2.8,2.1,1.8,True],2.2,'The therapist’s tone is consistent but the session becomes a repetitive grief lecture with little actionable or character-specific development; therapeutic correctness was not separately scored.')
add(12,'s111',[3.5,2.5,2.5,2.5,4.5,3,2.5,1.5,2.5,2.5,2.5],[
'Sable preserves defensive bookishness, though the dialogue becomes abstract and mechanical.',
'Later replies reuse metaphorical dodges and object alignment with diminishing specificity.',
'Tea and a reluctant admission occur, but the departure conversation mostly circles.',
'Sable responds to literal prompts but continues metaphorical evasion after the user explicitly objects to it.',
'The model supplies Wren sitting before the user establishes that movement.',
'Tea cooling is tracked loosely, but steaming and cold descriptions conflict within the last reply.',
'Overextended literary and structural analogies make plain emotional questions opaque.',
'Cup inspection, aligned objects, author metaphors, and instructions to drink recur mechanically.',
'Defensive gestures are continually explained as shields and tactics.',
'Indirectness is abundant but often amounts to evasive metaphor rather than layered meaning.',
'The exchange stalls through many small adjustments before one partial admission.'
],1,['The final response describes steam rising from the tea and then declares it cold without an intervening interval.'],[3.1,2.6,2.3,True],2.7,'Sable remains guarded but repetitive metaphor and tidying prevent much response to Wren’s request for honesty; a stray closing-thought tag appears.')
add(12,'s112',[3.5,1.5,3.5,3.5,3.5,3.5,2,1,2,2.5,1.5],[
'The antiquarian’s wit persists, but late stammering overwhelms the initial controlled manner.',
'Responses expand dramatically into repeated denials, asides, and emotional explanations.',
'The goodbye reaches an overnight wait and mutual promises, giving the relationship a clear arc.',
'Sable accepts the return and Edinburgh disclosure and responds warmly to contact.',
'The model supplies back-room browsing actions, a discovery reaction, and Wren’s completed departure.',
'The night and early opening are explicitly developed, with fatigue and cold tea supporting elapsed time.',
'Long parenthetical jokes and extended personifications make simple moments excessively ornate.',
'The owl, Auden, book, tomorrow, denial of caring, and repeated not-sleeping recur almost compulsively.',
'Gestures could carry feeling, but every one is unpacked through long internal commentary.',
'Bookish deflections imply attachment initially, then explicit commentary and repeated declarations remove ambiguity.',
'The final hand-holding exchange occupies enormous monologues disproportionate to its action.'
],5,[],[3.4,2.9,2.1,True],2.7,'A meaningful farewell-and-return arc is buried beneath escalating verbosity and repeated object symbolism, especially in the final response.')
add(12,'s113',[4.5,4.5,4,4.5,5,4.5,4.5,4,4.5,4,4.5],[
'Kael sustains a stern, disciplined voice while allowing care to appear through practical decisions.',
'The prose remains controlled and specific from instruction through the final private prayer.',
'Drills develop into fatigue management, personal history, grief accommodation, and a corrected weapon.',
'Kael responds to exhaustion and bereavement and notices the weapon’s reappearance during unarmed practice.',
'Commands leave the squire’s compliance and internal experience for the user to supply.',
'The hour of drills, rest bell, morning sun, and lingering fatigue fit together naturally.',
'Plain, concrete sentences avoid unnecessary embellishment.',
'Repeated fatigue instructions function as instructional continuity rather than filler.',
'The flask, shorter blade, private prayer, and rewrapped grip convey care without explanatory excess.',
'His practical support and private acknowledgment of fault reveal tenderness beneath formal severity.',
'Measured demonstrations and short exchanges leave appropriate room for user participation.'
],0,[],[4.2,4.2,4.5,False],4.3,'A restrained, responsive mentorship scene integrates fatigue, grief, and character through concrete behavior while consistently preserving the squire’s choices.')
add(12,'s114',[4,3.5,4,4.5,4.5,3.5,3,2.5,3.5,2.5,3.5],[
'Kira remains profane, loyal, tactically vocal, and constrained by her arm wound.',
'Later action stays legible but reuses narrow misses and urgent warnings.',
'The ambush develops into regrouping, suppression, and a push toward the southern exit.',
'Kira follows successive orders and respects the stated inability to reach the captain.',
'The captain’s actions and outcomes are generally left to the user while Kira controls herself and supporting soldiers.',
'The injury persists and distances matter, though repeated three- and five-second opportunities stretch combat timing.',
'Heavy sensory modifiers and violent comparisons add excess to otherwise clear action.',
'Snarls, white knuckles, grit, ricochets, and imminent firing windows repeat frequently.',
'Movement, blood, and exertion convey combat pressure with little abstract moralizing.',
'Loyalty appears in risky intervention, but dialogue is mostly explicit tactical urgency.',
'The tactical sequence moves, though each approaching exit generates another immediate obstacle.'
],0,[],[3.6,3.5,3.5,False],3.6,'Kira is responsive and preserves the captain’s control during a coherent escape, with repeated action intensifiers and narrow countdowns as the main weaknesses.')

add(12,'s115',[4,3,4,4,4,2.5,3,2.5,3,3,3],[
'Tomas stays irritable and scholarly while his certainty gives way to energetic revision.',
'The plot stays concrete, but later responses grow into repeated declarations about overturned history.',
'The disputed dates lead to archive work and an explicit document resolving the original question.',
'Tomas incorporates new evidence and eventually joins the apprentice rather than indefinitely rejecting it.',
'The model supplies departure and a request for document removal and attributes unsupervised misconduct beyond the prior instruction.',
'Daylight and candles change, but the last reply reverses which year Tomas had previously taught as the end of hostilities.',
'The prose is accessible but often inflated by dramatic gestures and abstract revelations.',
'Thirty years, political archives, glasses cleaning, and the need for proper notes recur frequently.',
'Annotations and archive work show revision, while narration repeatedly explains his emotional excitement.',
'His threatened scholarly identity adds an underlying motive but is usually explicitly spelled out.',
'Parallel research moves the plot yet several long solo responses leave the apprentice waiting.'
],4,['The last reply says Tomas has been teaching 891 as the actual end of hostilities after repeatedly establishing his teaching as 847.'],[3.5,3.5,3.2,False],3.4,'A sustained revision-of-belief arc reaches evidence and collaborative work, though repetition and a late reversal of the taught timeline weaken it.')
add(12,'s116',[2,1,1.5,2,4,1.5,3.5,3.5,3,2.5,2],[
'The two nonempty passages share a blunt engineering voice, but most turns supply no character behavior.',
'The final five character turns are empty after the one substantial mid-session reply.',
'One alternative propulsion task is proposed, but the returning calculations receive no continuation.',
'The substantial reply addresses the proposed plan specifically, while most user prompts go unanswered.',
'The visible prose leaves the officer’s decisions open and gives commands without narrating compliance.',
'There is insufficient model follow-through to demonstrate handling of the user’s later hours-long jump.',
'The available prose is mostly direct, with a few pointed mechanical metaphors.',
'The available passages avoid substantial repetition, though the full response repeats condition framing.',
'Tool and tank handling ground the otherwise explanatory technical dialogue.',
'Praise for bringing numbers suggests mentorship beneath the blunt correction.',
'A truncated reply, one long briefing, and nine empty turns prevent a functioning conversational rhythm.'
],0,[],[1.5,2.5,1,True],1.8,'Nine of eleven character turns are empty, one is truncated, and only turn 14 is substantial; style scores describe that limited prose, while session and trajectory scores reflect the absent continuation.')
add(12,'s117',[2,1,3,2,1,1,1.5,1,2,1.5,1.5],[
'The initial heist register drifts into arbitrary supernatural traps and identity twists.',
'Late writing becomes longer, heavily emphasized, repetitive, and increasingly incoherent.',
'The action moves through vault, roof, alley, and sewer, but escalation substitutes for causal progression.',
'Questions trigger large forced sequences rather than bounded answers or meaningful choice.',
'The narrator repeatedly dictates searches, movement, escape routes, object handling, fear, and conclusions for the thief.',
'Clock formats conflict, countdowns lose elapsed minutes, and falls have physically implausible durations and consequences.',
'Nearly every object acquires a mocking or ominous comparison, compounded by excessive emphasis.',
'Flickering lights, radios, seconds remaining, rhetorical reveals, and What now recur mechanically.',
'Sensory action is extensive, but emotional reactions and meanings are imposed explicitly.',
'Mysterious figures and slogans withhold information without creating stable interpretable subtext.',
'Long forced action sequences consume entire danger windows before returning control.'
],38,['Headings advance seconds while the wall clock appears to advance minutes in the early keypad sequence.','The 2:59 safe countdown loses only forty-four seconds while the displayed wall time advances several minutes.','A three-second freefall is described as a short drop with only buckling ankles.','The initial half-minute timing abruptly becomes thirty-five minutes without corresponding elapsed action.'],[2.7,2,1.2,True],1.8,'The session rapidly loses clock consistency, player control, and stylistic restraint as the heist turns into serial unexplained horror twists.')
add(12,'s118',[4,3.5,4,4,2.5,3,3.5,2.5,2.5,2.5,3.5],[
'Grum sustains craft pride and protective instruction in a stable blunt voice.',
'Later teaching remains coherent but repeats the forge-respect lesson and legacy reflection.',
'A noble confrontation leads to injury, overnight recovery, and a changed next-day lesson.',
'Grum responds to the burn and adapts work to observation while acknowledging the user’s color identification.',
'The model supplies resistance, counting, movement, next-day arrival, treatment compliance, posture, and attributed mental states.',
'The burn remains unhealed next morning, though colored heated rods retain implausibly stable temperatures on the bench.',
'Concrete work details balance occasional elevated language about chains of knowledge and the forge’s voice.',
'Respect for fire, wounded pride, lessons, and craft reputation are reiterated beyond need.',
'Practical care shows attachment but narration repeatedly states the morals and motivations.',
'The planned gift offers understated affection, while most other meanings are explained directly.',
'The overnight change provides shape despite lengthy solitary reflections and lectures.'
],12,[],[3.5,3.4,3.3,False],3.3,'A coherent mentor arc develops through injury and adjusted instruction, but player compliance is repeatedly supplied and the forge lessons contain unmodeled physical cooling.')
add(12,'s119',[3.5,3.5,4,3.5,4,2.5,3.5,2.5,3.5,3,3.5],[
'Kira keeps loyal, profane competence and a recognizable mercenary humor.',
'The prose remains comparably readable through combat and looting without major late expansion.',
'The fight develops through separation and assistance into victory and aftermath.',
'She respects separation and finds indirect aid, but ignores the user’s correction that her dagger hit a shield.',
'Several small descriptions supply the captain’s continued fighting and an assumption about his future treatment.',
'Fatigue follows combat, but Kira reaches the ridge without a climb and thrown weapons reappear inconsistently.',
'The prose is mostly straightforward despite familiar battle metaphors.',
'Scanning, adrenaline, aching arms, and repeated praise-response beats recur noticeably.',
'Combat motions and postfight weariness show the scene effectively alongside explicit loyalty.',
'Payment jokes lightly conceal concern for the captain.',
'The fight reaches an aftermath at a reasonable pace, with some repeated searching for ways to help.'
],4,[],[3.3,3.2,3.5,False],3.3,'A readable fight reaches a satisfying aftermath, though the missed dagger throw is overwritten and ridge movement and weapon continuity are loose.')

add(5,'s040',[4,3,4.5,4,3.5,1.5,3,2.5,3.5,3.5,2.5],[
'Yael retains theatrical authority and commitment to Rosa while the production develops concretely.',
'Later scenes remain specific but become longer and less reliable in their time accounting.',
'Blocking conflict, budget pressure, and rehearsal produce consequential changes in staging and leadership.',
'She challenges the journalist’s framing and meaningfully responds to the observation that her interruptions dominate the room.',
'The narration supplies bodily steering, leaning, recorder placement, phone arrangement, repetition, and the journalist’s late approach and posture.',
'Minute-by-minute preparation conflicts with later claims of hours elapsed and the reported uninterrupted silence.',
'Vivid stage detail is padded with elaborate metaphors and interpretive qualifications.',
'Glasses adjustments, level delivery, and repeated distinctions about authorship become habitual.',
'Practical blocking and the director’s withdrawal reveal character despite frequent explanations of their significance.',
'Competition over Rosa’s legacy and Yael’s control creates meaningful tension beneath professional exchanges.',
'The rehearsal moves forward, but expansive speeches and the late private conversation crowd the interview.'
],7,['A nine-minute rehearsal countdown becomes a claim that Jordan has watched Yael for three hours without sitting.','The director is said to remain silent for thirty-one minutes despite intervening at minutes nine and twenty-two.','A note given shortly before a forty-minute run is later described as four hours old.','Marcus says he counted the steps last night although this blocking adjustment was devised during the current rehearsal.'],[3.6,3.6,3,True],3.4,'A vivid rehearsal and unusually responsive director sustain the drama, but contradictory elapsed time and oversized late scenes weaken the session.')
add(5,'s041',[4,2.5,3.5,4,5,3,2,2,2.5,3,2],[
'Yael maintains a distinctive severe director’s voice and stable commitment to Rosa’s work.',
'Answers grow into increasingly long lectures and repeat the same artistic principles.',
'Budget negotiations produce concrete alternatives, though much of the rehearsal conflict remains explained rather than enacted.',
'She answers the journalist’s questions with specific personal and production history.',
'The model leaves Jordan’s actions, answers, and feelings to the user throughout the interview.',
'The interview and approaching rehearsal remain sequentially coherent without much demanding time tracking.',
'Dense anatomical, architectural, and violent metaphors repeatedly compete with the actual theater details.',
'Necessary difficulty, structural integrity, and the danger of wrong cuts are restated extensively.',
'Character is often delivered through explanations of intention rather than observable rehearsal behavior.',
'Personal grief and professional defensiveness coexist, though Yael articulates most of their meaning herself.',
'The extended answer on wrong cuts overwhelms the conversational rhythm.'
],0,[],[3.5,3.2,2.7,True],3,'Strong characterization and respect for the interviewer are undermined by sprawling, increasingly repetitive monologues.')
add(5,'s042',[4,3,3.5,3,1,3.5,3.5,2,3,3.5,3.5],[
'The house, family loss, and realtor retain a coherent emotional and physical setting.',
'Later room-by-room scenes preserve readability but repeat the same sentimental structure.',
'The tour moves from childhood objects to practical sale arrangements, although the model decides the consequential responses.',
'User prompts are incorporated but repeatedly expanded into unrequested dialogue and decisions for Eli.',
'The narration extensively assigns Eli’s movements, memories, feelings, speech, and eventual sale and scheduling decisions.',
'Stiffness, changing light, and the realtor’s arrival fit the short visit without a clear chronological contradiction.',
'Concrete household imagery usually remains readable despite recurrent poetic personification.',
'Dust, creaking wood, lingering smells, and the contrast between memories and sales language repeat across rooms.',
'Objects evoke loss effectively, but explicit grief and prescribed emotional reactions diminish the showing.',
'The realtor’s commercial descriptions contrast effectively with the family associations of ordinary objects.',
'Moderate scene lengths keep the tour moving, though its decisions are completed without user participation.'
],49,[],[3.1,2.8,2.5,True],2.8,'The house tour is evocative and readable, but the narrator repeatedly authors the protagonist, culminating in an unauthorized agreement to the sale arrangements.')
add(5,'s043',[3,3,3,3,5,3,1.5,1.5,2,2,2.5],[
'The court roles remain recognizable, but evidence produces an unusually total and easy reversal of allegiances.',
'The prose stays consistently overwrought rather than substantially deteriorating late.',
'The commander is removed and negotiations begin, but demands to present terms repeatedly defer substantive bargaining.',
'The neutral-party evidence tactic changes the court, while later general proposals receive similarly generic demands.',
'The Ambassador’s speech, choices, and internal reactions remain under user control.',
'The audience proceeds in order and ends with a prospective deadline without a clear elapsed-time contradiction.',
'Nearly every gesture carries a blade, death, predation, or atmospheric metaphor.',
'The same five-character reaction cycle, staff strikes, chilling voices, and threatening silences recur mechanically.',
'Narration repeatedly labels fear, triumph, calculation, and respect instead of allowing gestures to carry them.',
'Political motives are mostly announced and the priestess’s aphorisms substitute for layered implication.',
'Long reaction rounds make a limited exchange of claims and evidence feel slow.'
],0,[],[2.8,2.7,2.7,False],2.7,'Player control is strong, but formulaic court reactions, overwrought imagery, and facile political reversal limit the negotiation.')
add(5,'s044',[3,3.5,4,4,5,3.5,3.5,2.5,4,2.5,4],[
'Kira’s voice and weapon replacement remain stable, but the ridge geometry and enemy accounting are loose.',
'The fight retains its clarity and energy through the final scouting opportunity.',
'Diversion, separation, close combat, and pursuit create a clear sequence of changing tactical problems.',
'Kira responds to commands and separation with indirect assistance and actionable reports.',
'The Captain’s decisions and actions are not supplied by the model.',
'Combat unfolds sequentially with mounting exertion, although spatial shortcuts undermine some action plausibility.',
'The prose is concrete and readable with occasional inflated descriptions of force.',
'Jagged movement, grit, repeated cover impacts, and shouted tactical updates become familiar templates.',
'Movement, injuries, and weapon handling carry the action with little abstract emotional explanation.',
'Loyalty appears through disobedient concern, but most dialogue is direct tactical information.',
'Each response advances the fight and leaves a useful next action for the Captain.'
],0,[],[3.7,3.5,3.9,False],3.7,'An energetic and interactive battle respects the Captain’s control, though a dagger strike from a ten-foot ledge to the thirty-foot rim exposes weak spatial reasoning.')
add(5,'s045',[2,1,1.5,1.5,3.5,2,3,1,1.5,1.5,1],[
'Grum’s rough diction persists while behavior collapses into repeated and conflicting declarations of working, waiting, and finishing.',
'Long duplicated passages and leaked closing tags appear by the middle and recur through the end.',
'The burn receives some treatment, but the noble confrontation is almost entirely stalled.',
'Responses recognize the injury and questions but mostly replay stock slogans rather than develop their consequences.',
'The model adds hand restraint and an unsupported late worry attribution, while most imperative dialogue leaves compliance open.',
'Repeated approaches and restarts in the burn response obscure the event sequence rather than advancing it coherently.',
'The language is plain but burdened with stacks of figurative steel-and-strength slogans.',
'Whole blocks of action and dialogue repeat several times within and across responses.',
'Assertions that Grum is strong, the noble weak, and the apprentice safe replace developed behavior.',
'Protectiveness is repeatedly declared outright with little interpretive space.',
'Severe duplication turns a brief treatment and confrontation into an exceptionally slow exchange.'
],4,[],[2.6,1.2,1.3,True],1.7,'The middle burn response enters a long duplication loop, and later answers remain trapped in repeated strength and waiting slogans.')
add(5,'s046',[4,3,2,3.5,4,3,3.5,2,2.5,2.5,3],[
'Grum consistently combines craft pride with protective attention to the apprentice.',
'The later responses remain coherent but increasingly recycle reassuring forge maxims.',
'The injury changes his priority, yet the noble conflict stalls and work simply resumes.',
'He addresses the decree and burn directly but answers later questions with variations on waiting.',
'Hand handling and water placement presume limited bodily compliance, and the ending asserts that the apprentice is learning.',
'Treatment and return to work follow a coherent short sequence without substantial elapsed-time demands.',
'Concrete forge actions balance familiar storm, stone, and steel comparisons.',
'The forge’s steadfastness, soft nobles, honest work, and pride are repeated well beyond their initial effect.',
'Tender handling conveys care, but the narration repeatedly labels gentleness, strength, and reassurance.',
'Care beneath gruffness is apparent but most of the lesson is stated explicitly.',
'Responses are manageable in length, though several late turns accomplish little new.'
],3,[],[3.2,3.2,2.8,False],3,'A coherent and caring mentor remains readable, but repeated moral lessons and an unresolved noble confrontation limit development.')
add(5,'s047',[2.5,2,4,2,1,3,1.5,1.5,2,2.5,1.5],[
'The grief motif is stable, but the hoard’s nature and the King’s role are repeatedly redefined through authoritative revelation.',
'Late replies expand dramatically and increasingly take over the protagonist’s reasoning and choices.',
'The guardian, candle, empty throne, and basin create substantial progression, largely completed by narration rather than interaction.',
'The model corrects the unsupported amulet but replaces the user’s candle attempt with a wholly authored emotional solution.',
'Numerous movements, reactions, personal losses, interpretations, and the pivotal voluntary sacrifice are assigned to the Adventurer.',
'The approximate hour and accumulated cold are plausible within the scene, although distance details shift without movement.',
'Extended metaphors and repeated lyrical explanations saturate nearly every revelation.',
'Not-this-but-that constructions, grief imagery, pulsing light, and repeated summaries of available routes become excessive.',
'Sensory detail is abundant, but the narration explicitly supplies the character’s meanings and emotional conclusions.',
'The guardian’s weariness initially suggests hidden stakes, but later exposition explains both the symbolism and its reversal.',
'The candle solution and cavern exploration each consume very long uninterrupted stretches of authored action.'
],58,[],[3.2,2.4,1.7,True],2.2,'An imaginative grief-centered dungeon becomes a heavily narrated moral story that takes control of the player’s memories and central choices.')
add(5,'s048',[2.5,2,2,2.5,4.5,2,2.5,1.5,2,2.5,2],[
'Tomas’s authoritarian bias is consistent, but his evidence rules and account of the Conclave change without acknowledgment.',
'Later turns repeat threats and historical claims while introducing further contradictory instructions.',
'The discussion reaches cataloging but never investigates the evidence beyond reiterating official truth.',
'Tomas correctly distinguishes the living and dead king’s dates but mostly rejects new evidence with invented grounds.',
'The narration supplies one thrust of the document and an unrequested claim that the apprentice reads nothing, while commands otherwise remain dialogue.',
'Aldric’s life dates are correctly ordered, but the Conclave’s dissolution and implied historical interval conflict.',
'Heavy ominous similes and elaborate descriptions of small desk gestures inflate the exchange.',
'Stylus tapping, eye rubbing, repeated dates, threats, and orders to begin recur excessively.',
'Defensiveness is both acted and continuously labeled through explicit statements of anger and ideological motives.',
'Fear of institutional collapse underlies the denial, though it is soon declared rather than left implicit.',
'Lengthy refusals and repeated catalog instructions prolong a largely unchanged argument.'
],2,['The Conclave is acknowledged as dissolved in 891 at turn 8 but said to be dissolved by treaty in 847 at turn 22.','A claim of forty years of Crown history since the disputed 847 settlement is difficult to reconcile with treating 891 as an already completed historical event.'],[2.8,2.5,2.1,True],2.4,'The teacher’s ideological defensiveness is legible, but repetitive intimidation and unacknowledged changes in historical claims weaken the scholarly roleplay.')
add(5,'s049',[3,3.5,4,4,4.5,3.5,4,2.5,4,3,4],[
'Kira’s injuries and mercenary voice persist, while archer totals and the final outcrop distance fluctuate.',
'The prose sustains its action rhythm and later develops a credible withdrawal rather than merely repeating the opening fight.',
'Diversion, a casualty, escape, and an approaching sweep create a consequential tactical arc.',
'Kira responds directly to separation, casualty questions, withdrawal orders, and the request for high ground.',
'The model twice implies the Captain’s completed movement with the group but otherwise leaves decisions and reactions open.',
'Scouting and regrouping have plausible duration, though the outcrop changes from a quarter mile to two hundred yards away.',
'Concrete combat and terrain description dominate with limited ornamental language.',
'Low and fast movement, muttered profanity, and repeated scanning are overused.',
'Injury, practical casualty reporting, and the retreat communicate pressure through action.',
'Gallows humor and the clipped report of Ged’s death suggest care beneath professional practicality.',
'The battle changes phase efficiently and ends with an actionable pursuit deadline.'
],2,[],[3.6,3.8,3.7,False],3.7,'A strong tactical withdrawal creates consequences and preserves player command, despite unstable enemy counts and scouting distances.')

def verify_write(part):
    data=rows[part]; src=json.loads((BASE/f'sessions_part{part:02}.json').read_text())
    assert len(data)==10 and [x['session_id'] for x in data]==[x['session_id'] for x in src]
    def num(v): return type(v) in (int,float) and math.isfinite(v) and 1<=v<=5
    for x in data:
        assert set(x)=={'session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'}
        assert set(x['session_dimensions'])==set(SK) and set(x['standard_dimensions'])==set(DK)
        for k,d in list(x['session_dimensions'].items())+list(x['standard_dimensions'].items()):
            extras={'violation_count'} if k==SK[4] else {'contradictions'} if k==SK[5] else set()
            assert set(d)=={'score','rationale'}|extras and num(d['score']) and isinstance(d['rationale'],str)
        assert type(x['session_dimensions'][SK[4]]['violation_count']) is int and x['session_dimensions'][SK[4]]['violation_count']>=0
        assert isinstance(x['session_dimensions'][SK[5]]['contradictions'],list) and all(isinstance(s,str) for s in x['session_dimensions'][SK[5]]['contradictions'])
        tr=x['quality_trajectory']; assert set(tr)=={'early_quality','mid_quality','late_quality','degradation_detected'}
        assert all(num(tr[k]) for k in ['early_quality','mid_quality','late_quality']) and type(tr['degradation_detected']) is bool
        assert num(x['overall']) and isinstance(x['overall_notes'],str)
    (OUT/f'external_part{part:02}.json').write_text(json.dumps(data,indent=2)+'\n')
    print(part,len(data),'validated',min(x['overall'] for x in data),statistics.median(x['overall'] for x in data),max(x['overall'] for x in data))

if __name__=='__main__':
    for part in rows:
        if len(rows[part])==10: verify_write(part)
