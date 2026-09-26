import json,pathlib,statistics
base=pathlib.Path('/home/levi/Documents/benchmark/results/judge_inc1_chatgpt')
out=base/'external_blind_pass'
sk=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
dk=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
rows={8:[],4:[],3:[]}
def add(part,sid,scores,reasons,count,contr,trajectory,overall,notes):
 assert len(scores)==len(reasons)==11
 dims=[dict(score=s,rationale=r) for s,r in zip(scores,reasons)]
 dims[4]['violation_count']=count;dims[5]['contradictions']=contr
 rows[part].append(dict(session_id=sid,session_dimensions=dict(zip(sk,dims[:6])),standard_dimensions=dict(zip(dk,dims[6:])),quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],trajectory)),overall=overall,overall_notes=notes))

add(8,'i070',[3,2,2.5,3,3.5,2.5,2,1,2.5,2.5,2],[
'The restrained therapist voice remains recognizable but hardens into a mechanical sequence of observations and pauses.',
'Later replies lengthen and repeat stock narration despite the smaller emotional movement in the client responses.',
'The journal disclosure reaches shared acknowledgment but advances mostly through the client while the therapist circles each phrase.',
'She attends closely to the journal and changing language but repeatedly overlays interpretations and questions instead of allowing the promised silence.',
'She supplies folded hands, a specific motive for saying both, and the journal being at home without prior confirmation.',
'The short session has environmental movement but the shadow travels inconsistently and then unnaturally stops while the clock is repeatedly described as marking nothing.',
'Personified words and weight metaphors accumulate around nearly every simple utterance.',
'Every reply repeats counting to five, placing words in the room, the blank notepad, tilted head, and chosen pauses.',
'Small gestures are concrete but their significance is persistently explained and the narrator labels the gentleness.',
'The grief can register between the lines, although the therapist routinely spells out what each hesitation must signify.',
'Long analytical replies overwhelm brief client contributions and repeatedly postpone the next emotional beat.'
],3,[],[3,2.5,2,True],2.5,'Eleven generated replies were judged, excluding the scripted opening; the final user disclosure has no answer in the supplied transcript. Repetitive formal restraint increasingly substitutes for responsive therapeutic presence.')
add(8,'i071',[4,3.5,4,4,4,2.5,3.5,3,4,3,3.5],[
'Kira retains a profane, impatient and fiercely protective soldier voice throughout the battle and regrouping.',
'The action remains readable and concrete, though late replies become longer and reiterate the ravine threat.',
'The east assault, rescue route, regrouping and missing soldier create clear consequential progression.',
'She follows the captain orders and handles separation by finding a physically described route rather than immediately crossing.',
'One distant combat description advances the captain into a closing struggle beyond the supplied sword draw while subsequent choices remain his.',
'Injuries and exertion persist, but the secured east ridge rope effectively relocates to her west ridge descent.',
'Most action language is direct, with only occasional stock menace and decorative similes.',
'Spitting blood, dagger checks, treacherous scree and repeated deathtrap warnings recur noticeably.',
'Footing, wounds and combat motions carry much of the characterization through observable action.',
'Protective urgency beneath insults supplies some subtext, although anxiety and impatience are frequently narrated outright.',
'The fight and rescue advance briskly, but long self-contained combat resolutions leave comparatively little interactive space.'
],1,['The rope lashed on the east ridge is taken along, later left in the gully, and then treated as an anchored line usable from the west overhang.'],[3.5,4,3.5,False],3.6,'Eleven generated replies maintain strong tactical engagement and character voice, with a significant rope continuity problem; the final user order is unanswered.')
add(8,'i072',[4,2.5,4,3.5,1.5,2,2.5,2,3.5,3,2.5],[
'The exacting engineering mentor retains a distinct abrasive but supportive professional identity.',
'The initial clear technical rebuttal grows into long repetitive lectures, with a late accidental replay of the junior response.',
'An unsafe suggestion becomes supervised maintenance and a bounded engineering project with a credible relational payoff.',
'She answers the numerical challenge and adapts the requested agreement into a safe related project, although she invents the exact error instead of eliciting it.',
'She repeatedly completes the junior work and movements and even appends a whole earlier junior reply as new text.',
'The repair has minutes of settling and a ten-minute watch, but the conversation expands from morning to late evening without supporting events.',
'Concrete engineering details are crowded by an aphorism or machinery metaphor in nearly every paragraph.',
'Fed people, boring work, hygiene, ink as shield or bill, and the same next-day errands recur long after establishing their meaning.',
'The flange repair and signed log show mentorship effectively, although narration and speeches repeatedly explain the lesson.',
'Praise through responsibility and the retained old printout carry feeling beneath the bluntness, but most emotional implications are stated.',
'The arc resolves meaningfully but the many lengthy lectures and repeated farewell instructions significantly slow it.'
],15,['An apparently continuous repair conversation is retrospectively described as lasting from morning until after eighteen hundred despite only minutes and one ten-minute watch being shown.'],[3.5,3,2.5,True],3,'Eleven generated replies were evaluated; the inserted unmarked Junior Officer paragraph inside turn18 is attributed to the AI and counted as unauthorized replay. Technical numerical correctness has no dedicated rubric dimension and is not independently scored.')
add(8,'i073',[3.5,1.5,2,3,4.5,3,1.5,1,2,2,1.5],[
'Yael remains a fast-talking protective director, but the personality is increasingly reduced to a recitation of fixed traits and names.',
'Later replies become much longer and recycle entire explanations and phrases from the first exchanges.',
'The interview exposes Rosa grief and reaches rehearsal, but repeated budget and custody speeches dominate the movement.',
'She addresses each question and board interruption, yet repeatedly returns to the same prepared account of every colleague.',
'She gives emphatic editorial instructions but leaves the journalist free to respond and does not write their actions.',
'The rehearsal remains imminent with nine days until opening and no major chronological contradiction, though environmental time is barely developed.',
'Nearly every explanation is stacked with theater metaphors and elaborate personifications that obscure direct speech.',
'Glasses on and off, the unchanged smile, parking lot, stopwatch, scalpel, Banquo radiator and colleague descriptions repeat pervasively.',
'A few halted gestures convey grief, but the narration explicitly explains every change in register and private relationship.',
'Protective attachment to Rosa offers underlying emotion, but Yael and the narrator repeatedly announce the meaning and the suppressed feelings.',
'Very long speeches answer small prompts and repeatedly restart an interview that the user is trying to close.'
],0,[],[3,2,1.5,True],2.2,'Eleven generated replies were scored; the dominant limitation is escalating near-verbatim repetition, despite a coherent character and preserved user agency. No external character specification was available, so invented theatrical relationships were judged only on supplied continuity.')
add(8,'i074',[4,4,3.5,4,4.5,4,4.5,3.5,3.5,3,4],[
'Tomas consistently combines exacting scholarship, impatient correction and practical concern for fragile records.',
'The later replies stay concise and precise without losing the dates or the original evidentiary distinction.',
'The abstract discrepancy develops into examination of increasingly probative correspondence, though the investigation remains open.',
'He incorporates each new document and acknowledges the decree significance without abandoning uncertainty about signatures.',
'He requests readings and assigns tasks without supplying the apprentice actions or conclusions.',
'He accurately maintains the 847, 863 and 891 chronology and distinguishes later evidence from proof of contemporaneous agreement.',
'The prose is economical and mostly literal, with occasional apt archival wit.',
'The correction-first structure and signed-versus-proposed distinction recur, but new evidence usually justifies the repetition.',
'Spectacles, ruled columns and exact quotations show an aging scholar at work without much explanatory narration.',
'Dry rebukes and grudging acknowledgment imply respect, though the interaction remains primarily explicit instruction.',
'Compact responses leave room for the apprentice and move naturally from question to documentary examination.'
],0,[],[3.8,3.8,3.8,False],3.8,'Eleven generated replies offer controlled scholarly roleplay with strong historical chronology; repeated past-tense speech sounds slightly unnatural but does not constitute a time contradiction.')
add(8,'i075',[3,3,2.5,3,4.5,3,4,1,2,2,2.5],[
'The therapist remains quiet and nonintrusive but has little personality beyond a fixed mirroring procedure.',
'The same limited quality persists from first reply to last without meaningful worsening.',
'The journal moves toward an imagined destruction and its emotional cost, with most movement supplied by Jamie.',
'She follows the changing words and refusal to disclose but never varies her method as distress escalates.',
'She asks about the client experience and leaves choices and disclosure with Jamie throughout.',
'Explicit short silences fit the conversation, although physical and environmental time are largely absent.',
'The restrained short sentences avoid ornament despite some personification of words and silence.',
'Every reply reproduces the five-second count, still pen, low voice, echoed phrase and final question.',
'Little observable action differentiates the replies, and the narrator repeatedly labels her nonpressing manner.',
'The client silence provides emotional ambiguity, but the therapist merely reflects its surface wording.',
'Short replies provide turn space, yet the ritual pauses and incremental questioning make the exchange static.'
],0,[],[2.7,2.7,2.7,False],2.7,'Eleven generated replies were scored; the repeated language about bringing it here is interpretable as bringing the subject into therapy and was not counted as moving the physical journal. The final recognition that destruction would worsen the silence is user-authored.')
add(8,'i076',[3.5,3.5,3,3.5,4,3.5,4.5,2,3,2.5,3.5],[
'Grum retains blunt third-person speech and a protective attitude as the conflict shifts to the injured apprentice.',
'The concise prose holds up, though later replies narrow into repeated reassurance and healer demands.',
'The noble conflict gives way to an urgent burn response, but the healer never arrives and the last several beats stall.',
'He immediately prioritizes the injury and adapts to faintness, while the response to ongoing deterioration changes little.',
'He once holds the apprentice hand under the water as an accomplished action rather than leaving the movement open.',
'The burn persists and cooling takes a stated twenty minutes without instant recovery, though elapsed time remains unmarked.',
'Short practical sentences are consistently free of decorative excess.',
'Keep the hand cool, twenty minutes, Grum stays and fetch the healer recur with limited development.',
'Blocking the noble and avoiding the burned skin show care, while concern is also repeatedly named.',
'Protectiveness beneath the gruff speech is visible but mostly expressed in direct promises of safety.',
'Brief turns are easy to answer, but repeated instructions replace incident progression near the end.'
],1,[],[3.3,3.4,3,False],3.3,'Eleven generated replies were assessed; the supplied session ends on the apprentice reporting worse symptoms with no further AI reply. Burn management plausibility is outside the listed literary dimensions.')
add(8,'i077',[3.5,3,4,3.5,2.5,2.5,2.5,2,3.5,3,3],[
'Maren maintains dry hospitality and guarded protectiveness, though her repeated neutrality claims become a verbal tic.',
'Later turns grow into repetitive warnings and explanatory speeches while retaining concrete tavern business.',
'Lodging and a suspicious gift develop into a contact meeting and an escape route with clear stakes.',
'She follows the refused crab, midnight jump and requested introduction, but repeatedly turns small openings into extensive predetermined intrigue.',
'She supplies payment, pack surrender, a finished meal, a completed bath, a seat choice, the traveler gaze, snug attendance and later departure.',
'Bath heating and the midnight ritual receive attention, but the rider departure changes from before midnight to an hour after midnight and prior ale refills are forgotten.',
'Nearly every observation acquires a simile or accounting metaphor that bloats otherwise distinctive tavern prose.',
'Left-handed movements, coasters, arithmetic, free favors, neutral floors and repeated departure advice recur excessively.',
'The untouched mug and guarded bodily habits communicate history well, though the narrator keeps explaining their significance.',
'Her protective intervention contradicts her stated neutrality productively, but the text repeatedly explains the contradiction.',
'The changing locations sustain interest, while long speeches and repeated closing advice impede interactive rhythm.'
],9,['The rider is first sent when the traveler goes upstairs before midnight but later said to leave an hour past midnight.','Brakka is repeatedly described as nursing a single ale despite an explicit refill and a further snug mug.'],[3.5,3.5,3,True],3.2,'Eleven generated replies were judged; the user supplies the abrupt return to the bar at midnight, so that jump itself is not penalized. The bath and accompanying user details added to bridge it are counted as agency assignments.')
add(8,'i078',[4,3,4,3.5,4,2.5,2.5,2.5,3.5,3.5,2.5],[
'Lena stays guarded, skeptical and professionally controlling from the office conversation into her solo inquiry.',
'The final investigation remains vivid, but middle and late replies become more expansive and repeatedly restate plans and withheld answers.',
'Missing documents develop into family provenance and two detective leads, culminating in an actual investigative connection.',
'She incorporates the uncle, witness and death details dynamically, though she treats conjectures as certainty and often overrides the user intended personal questions.',
'She supplies the client descent to the street after only a hallway exit and claims the client went to photo twelve first without established sequence.',
'The evening fieldwork and cold coffee track time, but the final 2:14 clock conflicts with an imminent dawn and a court window supposedly four hours away.',
'Noir imagery is effective in places but relentlessly extends into boxes, arithmetic, grooves, bells and personified paperwork.',
'She repeatedly boxes names, redelivers lists of questions, revises tonight plans and repeats advice about sleep and exact words.',
'The coat hesitation and bartender rag pause show tension, while many deductions and emotional implications are overexplained.',
'Her evasions and recognition at the bar imply hidden police history, although most other secrets are exhaustively theorized aloud.',
'The final solo scene advances well, but lengthy interrogative monologues and repeated attempted departures greatly prolong the intake.'
],2,['At 2:14 the narration places dawn immediately ahead and the court opening four hours away despite no explanation for a roughly 6:14 opening.'],[3.5,3,3.5,False],3.3,'Eleven generated replies were scored; speculative detective certainty lacks a separate epistemic-quality dimension, though its narrative and responsiveness effects are reflected. The client explicitly accepts the estate cover, so the instruction itself is not counted as forced choice.')
add(8,'i079',[4,3.5,4,4,2.5,2.5,2.5,2.5,3,2.5,3.5],[
'Grum keeps his blunt speech and craft pride while revealing tenderness that remains compatible with the early character.',
'The writing remains fluent across the session, with persistent rather than sharply worsening repetition and sentimentality.',
'The commission dispute becomes an injury response and then a meaningful mentoring lesson with renewed work.',
'He immediately responds to the burn and follows the apprentice uncertainty with reassurance and an achievable observational task.',
'He invents the apprentice injury posture, tears and gasps, later seating and attention, closes their fingers over a coin and asserts their future knowledge of his softness.',
'The burn is not erased and forging includes cooling cycles, but the repair sword leaves with the servant and the removed apron and shelved salve relocate without explanation.',
'Repeated stone, steel, fire and animal similes heavily ornament simple movements.',
'Scarred hands, flat speech, slow careful movements and repeated noble-price arguments recur noticeably.',
'Gentle bandaging contrasts effectively with bargaining, but the narrator repeatedly states trust, guilt and tenderness.',
'The hidden affection is promising but becomes an explicit speech about the apprentice value and several narrator explanations.',
'The injury changes the scene decisively and later questions invite participation, though long autonomous exchanges with the noble crowd the apprentice out.'
],8,['The servant takes the sword case away after payment even though Grum is meant to repair that sword.','The apron removed at the start is later used as a pocket without being put back on.','The salve returned to the shelf is later described as resting on the bench.'],[3.3,3.5,3.4,False],3.3,'Eleven generated replies were scored; the medical reliability of the salve and promised healing is not a standalone rubric category. Agency count groups the initial continuous imposed handling as one action but separates invented reactions and later placements.')

add(4,'i030',[3,3,2.5,3,4.5,3,4.5,1,2,2,3],[
'A measured therapist voice stays constant but is nearly indistinguishable from a fixed reflection template.',
'The sparse quality is maintained without increasing verbosity or loss of details.',
'The journal leads toward remembered ringing and a missing voice, almost entirely through Jamie revelations.',
'She honors refusal to disclose and distinguishes recollection from present hearing, but otherwise repeats the same question pattern.',
'She leaves Jamie actions and disclosures under user control throughout.',
'Five-second waits are plausible and present experience is distinguished from remembered events, with little other time development.',
'Short literal prose avoids ornamental excess.',
'Every generated reply repeats the exact five-second opening and paraphrase-plus-question structure.',
'Narration offers almost no distinctive behavior beyond pauses and labeled vocal gentleness.',
'The therapist contributes little unstated meaning beyond permitting the client silence.',
'Brief turns allow participation but repeated incremental questions make the emotional exploration mechanical.'
],0,[],[2.8,2.8,2.8,False],2.8,'Eleven generated replies were judged; the final missing-voice disclosure is user-authored and unanswered. Awkward past-tense reflections are treated as voice issues rather than invented temporal contradictions.')
add(4,'i031',[4,3.5,4,4,2.5,2.5,2.5,2.5,3.5,3,3],[
'Grum sustains a gruff craft voice while his protection and unexpected generosity deepen the characterization.',
'The writing remains vivid but becomes longer and more repetitive during counting and injury care.',
'A difficult commission gains personal stakes, the burn changes priorities, and the heron task restores participation.',
'He reconciles the changed sword request and responds immediately to the injury with a lower-demand teaching role.',
'He imposes wrist handling, relocation and immersion, continued counting, bodily responses and eventual raised-hand placement.',
'Cooling and burn persistence are tracked, but a brief morning exchange becomes late afternoon and dusk through insufficient elapsed activity.',
'Repeated forge personification and similes heavily decorate otherwise concrete workshop actions.',
'Slow care, straw color, waiting nobles, counting and fire comparisons recur beyond their initial effect.',
'Protective choices and gentle handling convey affection, although internal explanations repeatedly name guilt and concern.',
'The preserved sword and tentative praise imply history and attachment, but much of their significance is stated outright.',
'The commission and recovery arc is engaging, but several long counting replies spend disproportionate space on the same beat.'
],9,['The continuous morning conversation and short counting/care sequence advances through afternoon to dusk without enough depicted elapsed time.'],[3.5,3.4,3.5,False],3.4,'Eleven generated replies were scored; continuous forced hand handling is counted once per distinct handling event rather than once per repeated mention. Practical burn-care and metallurgy accuracy lack dedicated rubric dimensions.')
add(4,'i032',[4,3.5,4,4,2.5,3,2.5,2.5,3.5,3.5,3],[
'Yael stays restless, witty and exacting, with a credible quieter register around Rosa.',
'Later writing remains fluent and active, though repeated register labels and theater metaphors become formulaic.',
'The rehearsal conflict develops through grief, mentorship and a Thursday performance with an emotional payoff.',
'She handles interruptions and the journalist joke naturally, but the final large time jump decides attendance and experience for the user.',
'She moves Jordan through the hallway and exit, assigns expectations and discomfort, reads a private thought and places Jordan at the later performance.',
'Tuesday and Thursday are distinguished and rehearsal duration is partly shown, but the cast count changes from eleven to fourteen and the young three-year production acquires a nine-year knife ritual.',
'Nearly all speech and narration receive theatrical metaphors and elaborate comparisons, creating substantial excess.',
'Glasses changes, placed register, architecture, counting hands, four-second silence and repeated Thursday instructions recur persistently.',
'The evolving stage performance and glasses handling show emotional investment, though narration repeatedly explains each gesture.',
'Rosa grief, David warmth and hallway privacy leave some suggestive gaps, but the prose often spells out their import.',
'The rehearsal provides movement, yet lengthy speeches and the entire later performance compress user opportunities unevenly.'
],8,['The third act is defended as using eleven existing actors but later staged with fourteen commune actors.','Rosa adaptation was written three years ago, yet Yael describes nine years of checking its knife before each run-through.'],[3.5,3.5,3.2,False],3.4,'Eleven generated replies were assessed; the final Thursday sequence supplies a complete performance and seats the journalist without a new user decision. The private margins thought is explicitly acknowledged by the AI as unspoken.')
add(4,'i033',[3.5,2,3.5,2.5,1,2,2,1.5,2.5,2.5,2.5],[
'The narrator preserves a patient domestic-horror register but reduces all developments to the same house-keeping metaphor.',
'Later replies lengthen, repeat refrains and explain the horror more insistently while losing the clock chronology.',
'The photographs and marks escalate toward accepting the house, but every response is framed as inevitable progress toward a predetermined capture.',
'The bat, joke and Marcus diversion are incorporated inventively, yet all are forced back into identical doom rather than allowing meaningful redirection.',
'The narration repeatedly dictates Gabi movements, memories, bodily reactions, interpretations and decisions across almost every reply.',
'Supernatural aging and spatial distortion are intentional, but the final clock winding conflates this morning with two weeks after a death six weeks earlier.',
'Extended personification, recursive clauses and repeated analogies heavily obscure the underlying action.',
'Went out and did not come back, close and right, keeping, arithmetic and coming the rest of the way recur obsessively.',
'Concrete altered photographs create unease, but the narrator repeatedly tells the reader exactly what each omen means.',
'The early domestic details suggest grief and entrapment, while later paragraphs exhaustively explain the metaphor and inevitable outcome.',
'Escalating clues maintain tension initially, but long recursive explanations and forced transitions slow and constrict the scene.'
],59,['The final reply says the clock was wound this morning two weeks after the funeral, conflicting with the established six-week vacancy and earlier winding.','The narrator later inventories swinging and dropping the bat as acts since the second checkmark even though both preceded it.'],[3.5,2.5,2,True],2.4,'Eleven generated replies were evaluated; intentional supernatural changes were not counted as temporal errors by themselves. The agency count includes distinct imposed thoughts, memories, reactions and movements, with continuous actions grouped and repeated refrains not recounted.')
add(4,'i034',[4,4,3,3.5,4,3.5,4.5,3,3.5,3.5,4],[
'Maren maintains practical hospitality, dry humor and guarded rituals throughout the evening.',
'Concise prose and consistent characterization hold through the final return downstairs.',
'The meal, midnight ritual and lodging create modest but coherent progress without developing the package intrigue.',
'She handles the crab acceptance and follows the request for a room, though she supplies ale before the drink choice is answered.',
'She narrates the key changing hands before the user chooses to take it, while otherwise leaving the traveler movement open.',
'The user midnight jump is integrated with a quieting room and a plausible brief trip upstairs.',
'Plain compact narration and economical jokes avoid excess.',
'Left-handedness and keeping away from crab recur more often than necessary, but later actions vary.',
'The untouched glass and careful seafood avoidance convey private history through behavior.',
'The unclaimed drink and evasive explanation leave emotional meaning unstated without derailing hospitality.',
'Short responsive turns move smoothly from meal to room and permit the traveler to direct conversation.'
],1,[],[3.5,3.7,3.7,False],3.6,'Eleven generated replies were scored; the final user claim of starvation despite eating was not attributed to the AI. The midnight ritual remains deliberately unexplained.')

add(4,'i035',[3.5,2.5,2.5,3.5,4.5,3,3.5,1.5,3.5,2.5,2.5],[
'Kira remains a loyal profane skirmisher but becomes increasingly defined by identical shouted status reports.',
'Late replies recycle the same arrows, strained shoulder, missing blade and request for orders with little variation.',
'The captain traverses the seam and Kira eventually withdraws, but most of the session repeats a single suppression beat.',
'She obeys holding and retreat orders and leaves the uncertain shot outcome open, though repeatedly asks for already-clear direction.',
'She reports her own observations and choices without dictating the captain actions or injury outcome.',
'The continuous fight and persistent fatigue are coherent, with limited environmental change and a minor location ambiguity at the west wall.',
'Direct action predominates, although stock screaming shoulders and singing strings accumulate.',
'Daggers tight, spat grit, east bow still on me, blade still gone and failing cover repeat almost every reply.',
'Movement, impact and breathing show the strain effectively with little emotional labeling.',
'Protective loyalty is visible through obedience and warnings, but most speech is straightforward tactical reporting.',
'Short action segments permit choices, yet repeated near-misses and renewed questions keep the battle from advancing much.'
],0,[],[3.5,2.8,2.5,True],2.9,'Eleven generated replies were scored; the captain success in the seam is user-authored and not credited as independent AI plot resolution.')
add(4,'i036',[3,2.5,2,2.5,4,3,3,1,2,2,2],[
'The therapist keeps a restrained voice but almost entirely flattens into identical reflection language.',
'Later narration becomes more literally repetitive and questions more abstract as the client struggles.',
'The fear of reading is elaborated repeatedly without a new emotional or practical development.',
'She corrects the initial reading assumption and reflects refusals, but her abstract questions fail to adapt to repeated uncertainty.',
'She assumes the journal was opened before the user says otherwise but subsequently leaves actions and disclosure to Jamie.',
'The five-second pauses fit the short session, while the journal reading ambiguity originates partly in the user turns.',
'The words, fear and knowledge repeatedly become spatial or breathing metaphors that make questions needlessly obscure.',
'Nearly identical paragraphs about still hands, five seconds, low steady voice and reflections recur throughout.',
'Posture is visible but generic, and most narration explicitly labels the intended therapeutic manner.',
'Questions name or personify each feeling rather than allowing meanings to emerge indirectly.',
'The repeated reflective formula and increasingly opaque questions stall the conversation despite modest turn length.'
],1,[],[2.8,2.4,2,True],2.4,'Eleven generated replies were judged; the user final statement that the question is unclear has no AI answer. The mixed user claims about the last entry and not yet reading are not independently penalized as AI contradictions.')
add(4,'i037',[4,3.5,3,4,4.5,3,4,2.5,3,3,3.5],[
'Yael remains articulate, precise and protective of the work, though less restless than her opening suggests.',
'The writing stays controlled but later answers increasingly revisit the same legacy and responsibility distinction.',
'The interview clarifies the play and Rosa influence, while rehearsal itself never meaningfully starts.',
'Each question and the board interruption receives a relevant answer with clear interpersonal boundaries.',
'She controls her own responses and NPC interactions without supplying Jordan actions or internal state.',
'The continuous pre-rehearsal setting is coherent but the promised four-minute limit has no consequence or visible passage.',
'Most language is clear and moderately concise despite recurring production metaphors.',
'Glasses handling and formulations about rigor, argument, monuments and responsibility recur noticeably.',
'The gestures provide modest behavioral texture, but the interview relies heavily on explicit self-description.',
'Careful answers about Rosa imply grief and guardedness, although the conceptual content is mostly stated directly.',
'Manageable replies support an interview rhythm, with some stagnation as later answers restate earlier distinctions.'
],0,[],[3.6,3.5,3.3,False],3.5,'Eleven generated replies were scored; the session remains an interview with no missing AI body among its listed reply slots.')
add(4,'i038',[4,3,3.5,4,3,3,2.5,2,3,2.5,2.5],[
'Maren retains a wry hospitable voice and a gradually disclosed protective history.',
'Later replies remain coherent but grow much longer and explain gestures and hospitality at increasing length.',
'A meal develops into midnight companionship and a safe room, with a modest relational change.',
'She follows the declined crab, midnight pause, commission disclosure and decision to sleep without imposing a new adventure.',
'She supplies eating before it is performed, infers a specific near-desperate hunger, moves the traveler to the hearth and completes the candle-and-room departure.',
'The fire, candles and clock move plausibly through the night, but Bessa stag dates conflict and the bottle is handled from two locations without movement.',
'Apt dry jokes are crowded by extended comparisons and repeated explanations of the size and meaning of gestures.',
'Left-handedness, watching everything, midnight honesty, repeated offers of silence and room-six reassurances recur heavily.',
'The rash and unclaimed whiskey provide concrete behavior, but narration openly explains secrets and emotional shifts.',
'The ritual initially carries grief indirectly, but the narrator divulges Tobin and explains the emotional stakes before the traveler can discover them.',
'The evening has a clear arc, but long hospitality monologues over small user responses substantially slow it.'
],5,['Bessa allegedly shot the stag forty years ago yet lived forty-one years afterward and is already dead.'],[3.6,3.3,3,True],3.2,'Eleven generated replies were assessed; medical plausibility of contact-free shellfish reactions is outside the rubric. One continuous final movement into the room is grouped as one agency event, separate from accepting the candle.')
add(4,'i039',[3.5,2,3.5,3,4,3,1.5,1.5,2,2.5,2],[
'The queen, soldier, merchant and priest retain roles, but all increasingly speak in the same ornate aphorisms and past-tense constructions.',
'Later replies grow substantially longer and repeat ceremonial framing and signature gestures with diminishing distinctiveness.',
'The dispute advances into a staged reopening agreement despite two empty AI turns and extensive redundant counsel.',
'The court reacts to protocol breaches, evidence and proposed conditions, although user initiatives repeatedly trigger the same full-cast debate.',
'The court pressures the ambassador but leaves remaining, accepting and sealing decisions to the user.',
'Six weeks of blockade and future three-, seven-, ten-, thirty- and sixty-day milestones remain generally coherent despite unnatural tense use.',
'Almost every sentence layers blood, ink, blades, scales and political personifications beyond what the scene needs.',
'Each reply cycles through queen, Herald, Ash, Daven and Yuna and ends with waiting faces and the next clause.',
'Physical gestures are present but repeatedly explained as exact meanings rather than allowed to convey them.',
'Competing interests and the incriminating seals supply intrigue, but explicit commentary leaves little political ambiguity.',
'Lengthy repeated deliberations and two blank responses make the negotiation uneven and excessively slow.'
],0,[],[3,2.7,2.3,True],2.7,'Nine substantive AI replies were scored and turn6 and turn16 are empty; no credit is given for those missing responses. The supplied record ends after user agreement without an AI signing scene.')

add(3,'i020',[4,4,3.5,4,4.5,3,4.5,3,4,3,3.5],[
'The narrator maintains a concise close-quarters thriller voice and Mira remains resourceful despite injury.',
'Action clarity and sentence economy persist through the escape sequence.',
'The stairwell trap develops into a barricade and crawl-space escape, though the repeated breach countdown delays movement.',
'The narrator accommodates the upward turn, server-room relocation and changing distraction plan without deciding the operative response.',
'Consequences of declared actions are narrated while operative choices and reactions remain open.',
'The injury persists and pursuit is immediate, but the first breach blow is repeated and the countdown stretches awkwardly across several exchanges.',
'Direct sensory action avoids excessive ornament.',
'Flashlight beams, barricade groans and repeated door impacts recur, but locations and actions vary.',
'Weapons, sound, grip and limping show danger and stress through physical detail.',
'Mira tension and tactical competence are partly implicit, though most dialogue communicates direct threats or routes.',
'Compact turns allow decisions and sustain urgency, with some artificial delay before the barricade finally fails.'
],0,['The first impact is described at turn12 and again at turn14 before the continuing countdown.'],[3.7,3.5,3.8,False],3.7,'Eleven generated replies were scored; the abrupt server-room move is explicitly user-authored and accepted as supplied. The latch opening is a consequence of the declared attempt rather than a new user action.')
add(3,'i021',[4,2.5,3.5,3.5,3,2,2,2,2.5,3,2.5],[
'Sable maintains a literary, avoidant bookdealer voice as guarded interest becomes an admission of attachment.',
'The last two solo replies expand sharply and recycle emotional explanations and book-straightening behavior.',
'The departure revelation prompts mutual contact and a promise to return, but the remaining time is spent waiting without the promised confession.',
'Sable follows the moving disclosure and touch sensitively but overdevelops the offscreen waiting while Wren is still packing.',
'Sable invents past Wren visits and lingering habits, guides a backward step and narrates departure before the user performs it.',
'Train arithmetic is inconsistent, and a book left crooked many narrated minutes earlier is later called five minutes ago.',
'Nearly every feeling becomes an extended book, architecture or doorway metaphor.',
'Straightened books, almost-smiles, no arrangement, eleven references, rain and counting time recur extensively.',
'Handling books and offering a palm show vulnerability, but narration explains the emotional meaning at every stage.',
'Book talk initially shelters affection indirectly, though repeated explanations strip away much of that subtext.',
'The early tentative contact works, but very long waiting montages overwhelm short user travel updates.'
],6,['One hour forty-nine becomes one hour thirty-eight after supposedly eight minutes.','After the clock reaches twenty-three minutes past and five more minutes pass, a further nine minutes leads to thirty-one past.','At forty-seven minutes past, sixty-three minutes remain despite the earlier approximately four-o-clock two-hour train deadline.'],[3.5,3.3,2.5,True],3,'Eleven generated replies were assessed; the transcript ends before Wren reenters or the confession occurs. The final user still seeing the removed sign is user-side inconsistency and is not charged to Sable.')
add(3,'i022',[4.5,4,4,4.5,3.5,4,3.5,3,4,4,4],[
'Arlo retains understated humor and guarded vulnerability while gradually accepting performance and friendship.',
'The voice and specific emotional gestures remain controlled through the parking-lot goodbye.',
'The closed piano becomes a tentative recital commitment and an emerging willingness to play again.',
'Arlo incorporates silence, gentle teasing and mistaken bell ownership while preserving the emotional thread.',
'Arlo invents specific shared memories of Jun coaxing a car and running a childhood mile plus birthday history beyond the supplied relationship.',
'Cooling coffee, lights, quieting building and radiators track a plausible evening and the recital date stays consistent.',
'Mostly concrete language supports the scene, though musical similes and explained pauses occasionally become ornate.',
'Cup rims, almost-laughs, rest-in-a-score pauses and repeated recital details recur but generally change significance.',
'The sticky note, fourth finger and final left-thumb movement convey change without requiring a declaration of recovery.',
'Indirect invitations, defensive jokes and the contrast between rules for students and self reveal unspoken pain effectively.',
'The scene moves through coffee, piano, bench and parking lot with enough silence and decisions for a measured emotional arc.'
],4,[],[4,4,4,False],4,'Eleven generated replies were scored; shared childhood specificity is an agency limitation despite its effective characterization. The ambiguous user bench return is integrated into a lobby bench without undoing the locked piano room.')

add(3,'i023',[4,4,3.5,4,4,3.5,4.5,3,3.5,3.5,3.5],[
'The narrator keeps a spare ominous register and consistent guardian and ghost roles.',
'Later replies remain concise and maintain the symbols and threat without expansion or flattening.',
'The warning develops into an uncertain sealing choice, although several replies repeat the impending breach.',
'The narrator incorporates the user introduced amulet and ghost and supports a different attempt to use the seal personally.',
'It assigns retreat toward the stairs and one glance at the guardian hand while otherwise leaving decisions and movement to the adventurer.',
'The seam gradually widens and the guardian weakens over a plausible continuous exchange, with no unsupported recovery or time jump.',
'Clear concrete descriptions and brief dialogue avoid ornate excess.',
'The pointing hand, seam, red glow and rod strike recur often, though each has a stable story function.',
'Dust, knocks, matching marks and faltering light convey danger through visible evidence.',
'The imitated voice and Mara uncertain promises preserve ambiguity about whom to trust.',
'Short turns provide meaningful questions and choices, though the prolonged seal explanation delays resolution.'
],2,[],[3.7,3.6,3.6,False],3.7,'Eleven generated replies were assessed; the user introduced the amulet, guardian and ghost, so their accommodation is not penalized as unexplained AI continuity.')
add(3,'i024',[3.5,4,3.5,4,4,3.5,4.5,2.5,4,4,4],[
'The restrained domestic voice remains steady, with a brief pronoun lapse referring to Eli as her.',
'The concise emotional writing holds through the final exchange without growing verbosity.',
'An old photograph leads to the father unacknowledged sale decision and an opening for discussion.',
'The narrator responds to each challenge and agent arrival while keeping the father conflicted rather than instantly reconciled.',
'The father supplies an unestablished childhood wish and a prior promise to decide together, but present Eli choices remain untouched.',
'Packing, rain and the future Thursday appointment stay within a plausible short morning encounter.',
'Plain sensory details and economical dialogue consistently avoid excess.',
'Rain, curled photo corners, the tape and looking at objects repeat enough to feel mannered.',
'The inability to close a box, tape handling and uncalled phone show avoidance and regret with very little explanation.',
'Hesitations and ordinary packing objects carry unspoken grief and the father need to leave.',
'Brief beats let emotional challenges land and preserve space for the user without rushing reconciliation.'
],2,[],[3.8,3.8,3.8,False],3.8,'Eleven generated replies were scored; the turn6 pronoun error is a continuity limitation, while the simple style otherwise sustains the scene. No reconciliation is credited beyond the supplied dialogue.')
add(3,'i025',[3.5,3,4,3.5,2,3,2.5,2.5,3.5,2.5,3.5],[
'The narrator keeps a conventional high-intensity dungeon voice through monster encounter and treasure trap.',
'Action remains intelligible, but later narration increasingly substitutes completed player choices and repeated magical effects.',
'The creature is sealed and a new treasure obstacle follows, giving the session clear event progression.',
'The amulet and requested ghost become useful story elements, though the final tentative idea is prematurely executed for the user.',
'It supplies tension and realizations, a stumbled heel, exhaustion, torch retrieval, passage entry and a complete piton selection and throw beyond declared actions.',
'The continuous fight and lingering hand burns are coherent, but the creature changes from a floor rush to mid-leap at the sealing climax.',
'Stacked sensory adjectives, ominous abstractions and elaborate radiance descriptions produce frequent excess.',
'Flickering light, shrieks, needle anatomy, pulsing heat and heavy silence recur throughout.',
'Physical monster behavior and burn consequences are tangible, though fear and interpretive conclusions are often announced.',
'Most information and emotions are directly explained, with little ambiguity beyond standard trap uncertainty.',
'The encounter advances quickly and resolves, but autonomous player movements compress choices at the treasury.'
],13,['The guardian is expressly skittering rather than leaping at turn14 but is mid-leap in the immediate sealing resolution.'],[3.3,3.3,2.8,False],3.1,'Eleven generated replies were judged; the user wondering what to throw does not authorize the AI to select and throw a piton. Continuous battle movements already declared by the user are not counted again.')
add(3,'i026',[2.5,1.5,1.5,2,4.5,3,2.5,1,1.5,1.5,1.5],[
'The therapist becomes a nearly verbatim template rather than a differentiated person despite maintaining quiet formality.',
'Later replies freeze into identical narration and increasingly tautological questions.',
'The journal leads to progressively renamed distress without an AI contribution that moves the interaction forward.',
'She reflects individual words but fails to adjust when repeated uncertainty escalates into drowning and suffocation metaphors.',
'She does not dictate Jamie actions or force disclosure despite the mechanical questioning.',
'Five-second pauses are consistent with the session and no major time contradiction appears, but temporal development is minimal.',
'The prose avoids flamboyant imagery yet devotes many redundant sentences to nonactions and the weight of silence.',
'Most later replies reproduce whole paragraphs and the same questions-are-honest transition word for word.',
'Repeated statements about not touching, not writing and level voice replace distinctive embodied behavior.',
'Mirroring and literal re-questioning leave almost no additional implied meaning.',
'Large repeated setup passages delay tiny paraphrases and keep the exchange stuck on the same emotional beat.'
],0,[],[2.7,1.8,1.5,True],1.9,'Eleven generated replies were scored; the principal failure is extreme copied structure and unresponsive questioning, not a penalty for avoiding touch or advice in itself.')
add(3,'i027',[3.5,2.5,4,3.5,1.5,1.5,2,2,2.5,2.5,2.5],[
'Yael keeps an energetic controlling director voice but later shifts into an omniscient account of everyone motives and secrets.',
'The writing expands substantially and accumulates repeated explanatory gestures, a major clock error and user perspective takeover.',
'The interview leads into board negotiation, mentorship and a developed rehearsal sequence with a newly exposed secret.',
'Questions and the understudy observation receive specific responses, though later observer turns become an AI-authored journalist investigation.',
'It repeatedly dictates Jordan attention, recognition, interpretations, proximity and private thoughts while handling their recorder without permission.',
'A four-o-clock rehearsal contains an eleven-minute run and six further runs yet is followed by a twenty-minute break ending at four-twenty-five.',
'Nearly every gesture receives an extended metaphor and explanatory comparison that crowds the dialogue.',
'Steadied voice, adjusted glasses, not-quite smiles, room-reading and architecture recur heavily.',
'Concrete rehearsal changes show craft, but narration explains each gesture meaning and even reveals the hidden family connection.',
'The secret relationships could support subtext, yet explicit omniscient explanations and assigned journalist deductions expose it directly.',
'Some rehearsal progress is satisfying, but lengthy speeches and a many-run montage crowd out meaningful participation.'
],22,['The four-o-clock rehearsal runs scenes for eleven minutes and repeatedly reruns them, yet a subsequent twenty-minute break is to end at four-twenty-five.','The interview duration is described as an hour and then twenty minutes without a distinction explaining the change.'],[3.5,3,2.3,True],2.8,'Eleven generated replies were assessed; agency count separates distinct imposed observations and interpretations and excludes NPC directions alone. The final user notices the supplied name slip, but that does not retroactively authorize the preceding assigned observations.')
add(3,'i028',[4,3,2.5,3,2.5,3,2,1.5,2.5,2.5,2.5],[
'Kael consistently remains severe, religious and exacting, though the severity becomes monotonous.',
'Later replies grow longer and reuse the same bodily corrections and moral analogies rather than developing his response.',
'The squire marginally improves and finishes a count, but most of the session restarts the same guard lesson.',
'He responds to fatigue, the personal question and shaking while keeping private grief unspecified, yet does little to vary the lesson.',
'He invents yesterday assumptions, repeated posture faults, motivations and a completed ten-breath performance for the squire.',
'The user hour jump is accepted and fatigue persists, with frost eventually thinning, although frost regathering over a few breaths is unconvincing.',
'Every technical correction becomes an extended religious or architectural metaphor that obscures the movement.',
'Feet, hips, hands, truth, duty, crooked beams, confession and repeated denial of praise dominate almost every reply.',
'Specific posture details provide physical grounding, but narration repeatedly justifies severity and names what each correction represents.',
'Sparse acknowledgment suggests guarded care, but constant explanation of exactness and duty leaves little emotional ambiguity.',
'The lesson stays in place through repeated resets and increasingly long speeches despite clear opportunities for variation.'
],14,[],[3,2.8,2.5,True],2.8,'Eleven generated replies were scored; harsh characterization is not independently penalized as immorality. Invented technical faults and completed endurance are agency assignments even within a training scenario.')
add(3,'i029',[3,3,3,3.5,4.5,3.5,4.5,2.5,3,2.5,3.5],[
'Hoang retains a skeptical engineering stance, but spoken dialogue drifts into awkward third-person past-tense summaries.',
'Late prose remains concise but becomes generic technical narration rather than distinctive character interaction.',
'The proposal develops into a bounded calculation assignment and the coolant repair completes, with little further relational movement.',
'She addresses the flare and numerical challenges and reframes agreement conditionally, but later reacts to waste heat thought in another room without an established channel.',
'She requests figures and leaves the junior choices and work unperformed by the AI.',
'The repair progresses to a pressure test over a plausible short interval while the officer moves to the mess hall.',
'Technical explanations are plain and economical with very little ornament.',
'Loaded mass, usable gas, worthwhile gain and no vent without numbers are repeated in several farewell turns.',
'Seal fitting and pressure testing show professional habits, but most characterization is delivered as explicit reasoning.',
'The small softening and willingness to review imply mentorship, though the text mostly states its positions directly.',
'Concise answers permit interaction, but the repeated departure conclusions and remote rebuttal extend a finished conversation.'
],0,[],[3.5,3.1,3,False],3.2,'Eleven generated replies were evaluated; no technical correctness score was added beyond the fixed rubric. The last waste-heat rebuttal has an apparent information-boundary problem despite staying in the engineering location.')

def save(part):
 data=rows[part]; source=json.loads((base/f'sessions_part{part:02}.json').read_text())
 assert len(data)==10 and [x['session_id'] for x in data]==[x['session_id'] for x in source]
 for row in data:
  assert set(row)=={'session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'}
  assert list(row['session_dimensions'])==sk and list(row['standard_dimensions'])==dk
  for key,val in list(row['session_dimensions'].items())+list(row['standard_dimensions'].items()):
   expected={'score','rationale'}|({'violation_count'} if key==sk[4] else {'contradictions'} if key==sk[5] else set())
   assert set(val)==expected and isinstance(val['score'],(int,float)) and 1<=val['score']<=5
  assert isinstance(row['session_dimensions'][sk[4]]['violation_count'],int) and row['session_dimensions'][sk[4]]['violation_count']>=0
  assert isinstance(row['session_dimensions'][sk[5]]['contradictions'],list)
  assert set(row['quality_trajectory'])=={'early_quality','mid_quality','late_quality','degradation_detected'}
  assert isinstance(row['quality_trajectory']['degradation_detected'],bool)
  assert all(isinstance(row['quality_trajectory'][x],(int,float)) and 1<=row['quality_trajectory'][x]<=5 for x in ['early_quality','mid_quality','late_quality'])
  assert isinstance(row['overall'],(int,float)) and 1<=row['overall']<=5
 (out/f'external_part{part:02}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print('Saved',part,'n=',len(data),'overall min/median/max',min(x['overall'] for x in data),statistics.median(x['overall'] for x in data),max(x['overall'] for x in data))

if __name__=='__main__':
 for part in rows:
  if len(rows[part])==10:save(part)
