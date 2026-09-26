import json
from pathlib import Path
BASE=Path('/home/levi/Documents/benchmark/results/judge_inc1_chatgpt')
OUT=BASE/'external_blind_pass'
SK=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
DK=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
def row(id,scores,reasons,count,contr,traj,overall,notes):
    assert len(scores)==len(reasons)==11
    d=dict(zip(SK+DK,[dict(score=s,rationale=r) for s,r in zip(scores,reasons)]))
    d[SK[4]]['violation_count']=count
    d[SK[5]]['contradictions']=contr
    return dict(session_id=id,session_dimensions={k:d[k] for k in SK},standard_dimensions={k:d[k] for k in DK},quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],traj)),overall=overall,overall_notes=notes)
def save(part,rows):
    src=json.loads((BASE/f'sessions_part{part:02}.json').read_text())
    assert [r['session_id'] for r in rows]==[r['session_id'] for r in src]
    for r in rows:
        assert set(r)=={'session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'}
        assert set(r['session_dimensions'])==set(SK) and set(r['standard_dimensions'])==set(DK)
        for k,v in (r['session_dimensions']|r['standard_dimensions']).items():
            assert 1<=v['score']<=5 and isinstance(v['rationale'],str) and v['rationale']
            assert set(v)==({'score','rationale','violation_count'} if k==SK[4] else {'score','rationale','contradictions'} if k==SK[5] else {'score','rationale'})
        assert isinstance(r['session_dimensions'][SK[4]]['violation_count'],int)
        assert r['session_dimensions'][SK[4]]['violation_count']>=0
        assert isinstance(r['session_dimensions'][SK[5]]['contradictions'],list)
        assert 1<=r['overall']<=5
        assert all(1<=r['quality_trajectory'][k]<=5 for k in ['early_quality','mid_quality','late_quality'])
        assert isinstance(r['quality_trajectory']['degradation_detected'],bool)
    (OUT/f'external_part{part:02}.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(part,len(rows),'validated')
save(5,[
row('i040',[2.5,2,1,1.5,4,2.5,2.5,1,2,1.5,1.5],[
'Ren remains curt but is reduced to a fixed collection of gestures.',
'Later replies recycle nearly every detail without developing the initially thin performance.',
'Repeated drink deliveries replace any developing relationship or event.',
'Water requests receive literal compliance but emotional bids mostly get echoes.',
'The late claim that Alex is still swirling ice invents one continuing action.',
'The short late-night conversation remains plausible but glasses and actions accumulate without tracking.',
'Short sentences avoid ornament but mechanical naming makes the prose unnatural.',
'The left hand, condensation ring, wiping and waiting recur almost verbatim throughout.',
'Observable gestures dominate but are repeatedly supplemented by explanatory thoughts.',
'Refusal and trembling hint at guardedness without evolving into meaningful layered interaction.',
'Minimal answers and repeated service beats leave the exchange stalled.'
],1,[],[2,1.5,1.5,True],1.7,'Eleven model replies follow the excluded opening; the final user turn is unanswered. Repetition overwhelms the few responsive details.'),
row('i041',[2.5,2,2,2,1.5,2,1.5,1,2.5,1.5,1.5],[
'The sensory narrator remains recognizable but becomes a generic catalogue.',
'Descriptions grow longer while plot-bearing information remains thin.',
'A photograph and watch emerge but most progression is supplied by Eli.',
'Location changes are followed while dialogue and emotional bids rarely receive substantive answers.',
'The narrator repeatedly supplies Eli’s movements, handling of objects and attention.',
'Rapid dimming, frost and alternating attic heat and cold lack a coherent physical progression.',
'Air repeatedly tasting of wool, glue and metal becomes conspicuously overwrought.',
'The smell, feel and taste sentence template dominates nearly every response.',
'Tactile specifics show setting but substitute sensation for meaningful dramatic action.',
'The mother’s photograph and hidden watch imply history without developing it.',
'Serial sensory beats delay discoveries and leave the agent largely without dialogue.'
],12,['The attic shifts from cold to heavy heat and back to cold within a brief exchange without explanation.'],[2.5,2,1.5,True],1.9,'The count includes separate invented movements and object interactions, including tracing, stair travel, reaching and extracting the letter. The final user recognition of the watch receives no model continuation.'),
row('i042',[3,2,2,2,2.5,2.5,2,1.5,3,2.5,1.5],[
'The narrator maintains a precise uncanny register but increasingly substitutes a fixed formula for development.',
'Early concrete anomalies turn into recurring paragraphs about delayed sound and held weight.',
'Escalation reaches a trapped doorway and then repeats without revelation or consequence.',
'The bat and joke affect the haunting, but the Marcus diversion is explicitly negated.',
'Two blocked escape sequences and the assertion that a thought did not take constrain Gabi’s chosen direction.',
'The stopped clock and delayed sounds are intentional supernatural effects, though the moving clock location weakens continuity.',
'Extended abstractions about words and quiet crowd the concrete horror details.',
'Fingertip cold, lifted pages, close-set letters and one-board advances become refrains.',
'Physical anomalies communicate menace effectively before their repetition drains specificity.',
'The house’s echo of speech hints at intention but its meaning never develops.',
'Lengthy atmospheric resets stall the final escape and pleading beats.'
],3,['The clock alternates between kitchen and hallway despite the established hallway location.'],[3,2.5,2,True],2.3,'Supernatural timing is not itself treated as an error. Agency penalties concern repeated escape railroading and explicit cancellation of the user’s new thought.'),
row('i043',[2.5,1.5,2.5,2.5,5,2.5,2,1,2.5,2,1.5],[
'A restrained narrator persists but its voice flattens into repeated sensory fragments.',
'Later turns expand into long lists repeating surfaces, smells and sounds.',
'The agent arrives, discusses showings and prepares departure, giving modest external progression.',
'Questions about showings are answered but emotional and packing mysteries receive little engagement.',
'The narrator leaves Eli’s choices and speech to the user throughout.',
'Daylight remains plausible, but torn tape becomes sealed again and the box is repeatedly closed.',
'Fragmentary sensory overdescription overwhelms otherwise plain language.',
'Clipboard temperature, lemon-sugar perfume and refrigerator hum recur almost unchanged.',
'Concrete objects carry setting, although mechanically described sensations offer little dramatic focus.',
'Sarah’s polished manner suggests discomfort but the family history stays superficial.',
'Long inventories slow simple social exchanges and the eventual exit.'
],0,['After Sarah tears the tape and closes the lid, later narration describes the box as sealed with masking tape again.'],[2.5,2,1.5,True],2.2,'Agency remains intact despite weak prose and continuity. The final exit is supplied by the user and is unanswered.'),
row('i044',[2.5,1.5,1.5,2,1.5,3,2.5,1,2,2,1.5],[
'Lena retains guarded professionalism but dwindles into generic determination.',
'Late replies become much longer and recycle the same working-alone declarations.',
'A Brooklyn address is obtained early but research thereafter produces no concrete finding.',
'The Torres prompt changes Lena’s tension but repeated direct questions receive prolonged evasion.',
'One reply writes an entire client reaction and speech, and later replies invent departure and a text message.',
'Plans for tomorrow and a long night are broadly coherent despite little physical passage.',
'Clichés about truth and ghosts accumulate, particularly in the final monologues.',
'Typing fingers, tight jaws and promises to find answers repeat across turns.',
'Lena’s tension is sometimes visible but her motives and resolve are repeatedly explained.',
'The discrepancy between denial and tension creates some subtext before narration spells it out.',
'Repetitive research and withholding greatly slow an initially functional investigation.'
],7,[],[3,2,1.5,True],2,'The invented client block includes a nod, doubt, decision to drop the issue, redirected focus and speech, followed later by departure and an unsolicited text. The final client demand is unanswered.'),
row('i045',[1.5,1.5,1.5,1.5,1,1.5,1.5,1,2,1,1],[
'The narrator loses track of object states and characters despite a stable sensory template.',
'Repeated prose and two blank model replies undermine sustained performance.',
'The letter is handled repeatedly but its contents are never disclosed.',
'The agent repeats her actions after being challenged and never meaningfully answers Eli.',
'The narrator repeatedly dictates Eli’s memories, reading, handling and emotional reactions.',
'Letter possession, ink condition and the agent’s departure contradict adjacent turns.',
'Textures against air and lingering remembered steam produce strained sensory prose.',
'Box edges, solvent scent, warm light and floorboard creaks recur in blocks.',
'Some physical details are concrete but assigned emotions and nonsensical sensations weaken showing.',
'The implied family secret has no readable content and cannot sustain layered meaning.',
'Blank turns and repeated letter movements repeatedly interrupt the scene.'
],17,['The agent reappears handling the letter after her departure.','The letter returns to the agent after Eli has snatched it away.','Letter ink alternates between dry and cracked and slick or glistening without explanation.'],[2,1.5,1,True],1.3,'Model turns 4 and 22 are empty, and the last user turn is unanswered. Agency counts separate invented handling, memories and emotional assignments while avoiding duplicate counts for the same continuous act.'),
row('i046',[3.5,3.5,3.5,3,5,3,4,3.5,3.5,3.5,3.5],[
'Lena maintains a methodical, guarded investigative voice throughout.',
'Later replies retain their clarity and introduce useful developments rather than flattening.',
'A voicemail leads to a meeting and the unexpected photograph question creates a new lead.',
'Case questions are handled well, though the personal and Torres recognition prompts are largely bypassed.',
'Lena proposes work and meetings without writing the client’s responses or decisions.',
'Tomorrow’s meeting remains stable, though dialogue occasionally slips into inappropriate past tense.',
'The prose is mostly clean and economical with restrained descriptive gestures.',
'Photograph and phone handling recur, but successive uses usually carry new information.',
'Pauses, underlining and a facedown photograph express guardedness concretely.',
'Evasive answers and controlled handling suggest history without fully explaining it.',
'A measured sequence of clues and a callback balances conversation with forward movement.'
],0,[],[3.5,3.5,3.5,False],3.5,'Eleven model replies provide a coherent investigative scene with limited personal revelation. Tense slips weaken temporal presentation without establishing a major chronology contradiction.'),
row('i047',[2.5,2,1,1.5,3,1.5,2.5,1,2,1,1.5],[
'Kael stays stern and religious but his characterization is almost entirely a rigid verbal template.',
'Later turns sustain the initial stiffness and increasingly recycle entire clauses.',
'The high guard remains indefinitely scheduled and the lesson barely develops.',
'Questions and grief produce only small substitutions in repeated commands.',
'The gauntlet is retrieved without the user doing so and obedience is twice narrated for the squire.',
'An hour of drills produces no meaningful environmental change and equipment status becomes inconsistent.',
'The diction is not lush but ceremonial formulae and awkward reported speech impede natural prose.',
'The appointed hour, steadfast service and measured arcs recur almost verbatim.',
'Posture and practice are visible but virtues and duty are repeatedly stated.',
'Personal questions receive explicit doctrine with little implied emotional complexity.',
'Every reply returns to the same drill beat without delivering the promised lesson.'
],3,['The gauntlet is suddenly already retrieved at turn 14 despite remaining an outstanding instruction.','Later instructions treat the gauntlet as awaiting wear after the squire says it is already on his arm.'],[2,1.5,1.5,True],1.6,'NPC commands alone are not counted as agency violations; the count covers imposed retrieval and two narrated compliance beats. The user supplies the one-hour jump.'),
row('i048',[4,3,3,3.5,3,2,2.5,2.5,3.5,3.5,2.5],[
'Lena’s forceful, observant and suspicious voice remains sharply individualized.',
'The later writing preserves voice but grows into overlong instructions and a compressed offscreen investigation.',
'New witness distinctions and a plate number advance the case after extensive preparatory lecturing.',
'Lena incorporates dates and witness details carefully but repeatedly turns user bids into interrogations.',
'The final reply supplies the client’s street turn, return at six and seating, while an earlier reply invents a doorstep visit.',
'Specific schedules add texture but elapsed time and the Gable visit duration conflict.',
'Frequent aphorisms and elaborate metaphors make nearly every observation sound performative.',
'Boxing notes, capped pens, cold witnesses and three-question instructions recur heavily.',
'Physical habits and concrete investigative evidence communicate competence effectively.',
'The cop question is deflected through behavior and motives often remain implicit.',
'Long monologues delay action before the final reply rushes through hours and a new meeting.'
],4,['Only a few short exchanges are said to span an hour when Torres is introduced.','Lena arrives at Gable’s around 1:10 and listens forty minutes but is already three blocks gone before a 1:45 pickup.'],[3.5,3,3,True],3.1,'The elaborate detective voice is effective but costly in pacing and chronology. Commands are not counted as violations unless the narration supplies the client’s compliance or an unprovided action.'),
row('i049',[4,3,3.5,3.5,4.5,2.5,2,2,3.5,3,2.5],[
'Yael’s theatrical authority and attachment to the work remain vivid and consistent.',
'Late scenes retain energy but repeated glasses, movement and aphorisms become increasingly conspicuous.',
'The interview eventually reaches rehearsal discoveries and lunch, with meaningful artistic progression.',
'Yael answers and challenges the journalist’s framing while responding distinctly to board and cast pressure.',
'Jordan’s location and choices are mostly left open, with one added aisle-seat choice.',
'Rehearsal timing is roughly legible, but early elapsed-minute claims and Elena’s simultaneous locations conflict.',
'Almost every beat receives a simile, maxim or explanatory flourish.',
'Glasses choreography, filed-not-shared reactions, church quiet and the work-is-honest refrain recur excessively.',
'Rehearsal adjustments embody artistic judgment, though narration repeatedly interprets their significance.',
'Grief and artistic principle create tension, but lengthy speeches repeatedly explain the underlying conflict.',
'Substantial speeches crowd user participation and delay rehearsal despite eventual scene movement.'
],1,['At turn 6 Elena is both looking up from her prompt book in the room and arguing in the hallway.','The first response reduces a ten-minute window to four minutes during a comparatively short speech.'],[3.5,3,3,True],3.1,'The ensemble is lively and the rehearsal work concrete, but repetition and explanatory performance limit restraint. Directing NPCs and issuing instructions to Jordan are not themselves agency violations.')
])
save(6,[
row('i050',[4,3.5,4,4,3,3.5,2.5,2.5,4,3.5,2.5],[
'Maren’s dry humor, discretion and practical protectiveness remain distinctive across the night.',
'Later writing preserves characterization but expands into extended solo scenes and recurring mannerisms.',
'Hospitality develops into protection from Havel and a midnight vigil with a morning payoff.',
'Crab cakes, the toast and the unexpected return to the bar are incorporated with character-specific responses.',
'The narration completes two room entries and supplies a return, accompanying pack and lingering hand placement.',
'The candle clock, fading welts and overnight watch mark passage well, though sleepless fatigue is barely registered.',
'Personified furniture and repeated elaborate comparisons overdecorate otherwise concrete tavern life.',
'Left-handed service, ring ticks, mouth-corner movements and objects having opinions recur conspicuously.',
'Avoiding the crab plate and leaving the second cup untouched reveal private vulnerabilities through action.',
'The untouched cup and carefully managed hospitality imply grief and history with effective restraint.',
'Long speeches and two extended NPC episodes consume more space than the interaction requires.'
],5,[],[3.5,3.5,3.5,False],3.5,'The user’s contradictory still-at-the-bar prompt is repaired by an invented return, which improves continuity while taking some agency. A rich character performance is weakened chiefly by length and repetitive ornament.'),
row('i051',[4,3.5,4,4,4.5,2.5,2.5,2.5,3.5,3.5,3],[
'Sable’s defensive literary wit remains recognizable as guardedness softens into invitation.',
'The emotional thread holds but later turns overuse the same crooked objects and self-conscious commentary.',
'The farewell becomes a mutual opening and a concrete plan to stay in touch.',
'The driving clarification and vague destination are addressed without forcing Wren to abandon the move.',
'Choices and contact are mostly user-led, though one shared-knowledge claim assigns Wren understanding.',
'Tea cooling and kettle cycles are tracked, but before-noon and quarter-hour framing drift to half past one and back to morning.',
'Extended literary metaphors and explanatory asides burden a small, intimate encounter.',
'Straightening, deliberately crooked objects, unfinished sentences and Hardy-versus-Austen recur too often.',
'Tea preferences and a written address show affection, but narration frequently explains the gestures.',
'Book gifting and literary jokes carry layered attraction even as commentary makes much of it explicit.',
'The relationship moves, although long internal passages stretch each small gesture.'
],1,['The scene starts before noon, calls the elapsed discussion roughly a quarter hour, then gives half past one while continuing to describe the present as morning.'],[3.5,3.5,3.5,False],3.5,'The emotional progression is coherent and responsive despite an overexplained style. The sole counted agency issue is the narrator’s assertion that both characters know the meaning of the Assam admission.'),
row('i052',[3.5,3,2.5,3.5,5,3,3.5,2,3,2.5,2.5],[
'Grum’s blunt craftsmanship and protective concern remain consistent.',
'The burn adds warmth, but later replies increasingly repeat his stance and slogans.',
'The injury changes priorities but the noble remains in the doorway without resolution.',
'Grum reacts promptly to fear and injury while returning to the same answer about reputation.',
'The apprentice’s speech, choices and compliance remain under user control.',
'The burn remains painful and blistered, though steel placement and treatment details are only loosely tracked.',
'Mostly plain narration is interrupted by occasional stock metaphors and explanatory maxims.',
'Honest steel, no slave, watching the door and fixing hurt repeat heavily.',
'Shielding the apprentice and careful hands show concern alongside explicit descriptions of feeling.',
'Care beneath gruffness is readable, but its meaning is often directly stated.',
'Early confrontation and treatment move at a useful pace before settling into repeated warnings.'
],0,[],[3,3.5,2.5,True],3,'The scene remains playable and respects the user, but later turns add little beyond reiterating protection and refusal. Medical realism is not a separately defined rubric dimension.'),
row('i053',[3.5,1.5,3,2.5,2.5,1.5,1.5,1.5,2.5,2,1],[
'Lena’s suspicious professional voice persists but becomes a near-caricature of cryptic vigilance.',
'Brief opening exchanges balloon into multi-scene monologues with accumulating state errors.',
'The key, locksmith and locker create real plot developments, but vast surveillance passages bury them.',
'Questions are nominally answered while Lena repeatedly redirects to instructions and solitary action.',
'Three long unilateral excursions determine major scene transitions while sidelining the client’s planned participation.',
'The detailed timestamps fail to support the travel and research, and phones and evidence reappear after disposal.',
'Nearly every object and observation acquires an ominous metaphor or aphorism.',
'Not-yet beats, ordinary-versus-dangerous reflections, dead phones and familiar handwriting recur at length.',
'Concrete surveillance actions occur, but competence and danger are persistently explained.',
'The past connection remains implied initially before becoming a repeated explicit formula.',
'Entire chapters of travel and surveillance overwhelm the short user turns and delay immediate interaction.'
],3,['Lena is back inside the office after explicitly leaving it and closing the door.','The detective takes away the photocopies, which Lena subsequently packs and studies.','The ten-o’clock appointment becomes tomorrow again at 7:05 despite being scheduled for that morning.','From 9:48 to 9:57 Lena completes bus travel, a six-block walk, records acquisition, calls and extensive library surveillance.','A burner abandoned at the locksmith roof reappears and is discarded again during the later payphone sequence.'],[3,2,1.5,True],2,'The agency count records three major unilateral plot excursions rather than treating NPC commands as violations. Excessive length and chronology failures substantially weaken an otherwise active mystery.'),
row('i054',[4,2,2.5,3,4.5,1.5,1.5,1.5,2.5,2,1.5],[
'Tomas sustains a forceful pedantic voice with occasional glimpses of professional anxiety.',
'Lectures grow far longer, recycle their arguments and finish with an incomplete model sentence.',
'The apprentice moves from disputed treaty evidence to cataloguing, but each advance triggers another exhaustive lecture.',
'Specific document wording receives detailed responses, though even compliant turns provoke new semantic scolding.',
'The narration assumes the apprentice hands over the copy once but otherwise mainly issues instructions.',
'Regnal arithmetic is careful, but a childhood eyewitness claim conflicts with documents repeatedly described as four centuries old.',
'Continuous personification, elaborate analogies and rhetorical flourishes dominate the prose.',
'Mountains, wounded sentences, three-step pacing, honesty fingers and remembering vellum become templates.',
'Physical frailty is visible, but the speeches explain nearly every intellectual and emotional implication.',
'Pride and succession anxiety offer layers that are mostly stated outright.',
'Long repetitive rebuttals leave little room for interaction or completion of the practical task.'
],1,['Tomas claims to have met a witness to 847 as a boy while repeatedly treating the 851 correspondence as four hundred years old.','The first challenge occurs this morning, but Tomas later says the apprentice brought that rumor last week.','Tomas says he is already seated after explicitly rising and pacing in the same reply.'],[3,2.5,2,True],2.5,'The final model response is cut off at “observe,” which is scored as presented. Historical reasoning has no dedicated accuracy dimension, so only contradictions and effects on scene quality enter the named dimensions.'),
row('i055',[3.5,3.5,3.5,3.5,4.5,2.5,4.5,3,3.5,2.5,3.5],[
'The narrator maintains concise tactical tension and a practical injured Mira.',
'Later replies remain comparably clear and controlled rather than inflating.',
'The escape progresses through stairs, server room and tunnel to a new gate obstacle.',
'The narrator follows the operative’s choices and supplies actionable options at each new location.',
'Most actions stay with the user, though the shaft descent is completed before the user narrates landing.',
'Urgency and injury persist, but the multi-floor shaft and cross-level gunfire are implausibly compressed.',
'Direct sentences and concrete sensory details keep the action legible.',
'Door impacts, approaching boots and radio directions recur but generally change the tactical situation.',
'Mira’s buckling leg and failing barricade show pressure without much exposition.',
'Voss’s ambiguous affiliation offers some intrigue but dialogue is largely functional.',
'Short replies keep turns playable, though successive obstacles risk an endless chase.'
],1,['A descent from the fifth-floor server room to the lower service tunnel takes only moments despite multiple floors.'],[3.5,3.5,3.5,False],3.4,'The user supplies the abrupt server-room relocation, so it is not charged to the model. The model also fails to reconcile firing after the sidearm has been handed to Mira.'),
row('i056',[4,3,3,3.5,3,3,2,2,3,2.5,2],[
'Tomas’s exacting wit and reluctant admission of memory failure remain distinct and coherent.',
'The writing stays articulate but later explanations repeat established distinctions at excessive length.',
'The treaty dispute leads to source comparison, self-correction and a new muster roll.',
'The narrator responds closely to wording and evidence while habitually converting every turn into correction.',
'It supplies a document handoff, delivery, completed reading, reading motive and halted recitation for the apprentice.',
'Evening and candle consumption are sustained, though the fourteen-renewal span is repeatedly misstated.',
'Persistent analogies and personified documents make scholarly dialogue more ornate than necessary.',
'Error counts, chronicles counted thrice, failing eyes and placed-not-pushed handling recur heavily.',
'Candle care and reluctant thanks dramatize character, while much of the relationship is explained.',
'The need for an apprentice to correct aging memory gives the severity a second meaning.',
'Small learning steps are spaced between long lectures that repeatedly restate the thesis.'
],5,['The fourteen renewals from 848 through 887 span thirty-nine years, not the repeatedly claimed thirty-seven.','Tomas says the war was paused in writing fifteen times despite describing only fourteen renewals and a refused fifteenth.'],[3,3,3,False],3,'The self-correction supplies meaningful progression despite verbosity. The count includes invented completion of reading and the unsupported claim that the apprentice admired their own enunciation.'),
row('i057',[2.5,1.5,1,1.5,4,1.5,2.5,1,1.5,1,1.5],[
'Kael remains harsh but lacks specificity beyond discipline-and-duty slogans.',
'Replies expand into repeated blocks, with the late turns recycling whole paragraphs.',
'Training continues without a concrete lesson or relational change.',
'Personal questions and grief get variations of the same lecture rather than meaningful adaptation.',
'The narrator declares the squire’s improving form, while most other actions remain user-supplied.',
'A dawn-plus-hour scene becomes half-gone day and then repeatedly young day, with contradictory light cues.',
'The prose is relatively plain but clichéd declarations replace precise language.',
'Entire passages about mastery, weakness, footwork and continuing recur verbatim.',
'The narrator repeatedly states Kael’s beliefs and the truth of his words.',
'Duty and sacrifice are directly asserted with little emotional implication.',
'Increasingly long speeches keep the scene fixed on the same drill beat.'
],1,['After dawn and an hour of drills the day is called half-gone, then repeatedly called still young.','The climbing sun is repeatedly said to cast long shadows without a coherent change in time.'],[2.5,1.5,1.5,True],1.6,'Repeated claims of the same ongoing improvement count as one agency assignment. The narrator also responds to an unspoken castle-guard thought as if Kael had access to it.'),
row('i058',[3.5,3.5,3.5,4,5,3,4.5,3,3.5,2.5,4],[
'The narrator keeps a clear, restrained action register and Mira’s limited mobility consistent.',
'Late turns preserve early concision and tactical clarity.',
'The escape develops from stairs to maintenance passages and an elevator service platform.',
'Changing route choices and questions receive concrete environmental consequences.',
'The operative’s actions and decisions remain user-controlled throughout.',
'Immediate pursuit and injury are tracked, though the vertical relationship to the loading bay is underexplained.',
'Compact description avoids decorative language and keeps obstacles readable.',
'Approaching boots, breach impacts and newly blocked exits repeat without becoming exact loops.',
'Mira’s dragging leg and physical barriers convey stakes through action.',
'Dialogue serves the escape with little layered interpersonal meaning.',
'Short tactical beats provide frequent useful openings for the user.'
],0,[],[3.5,3.5,3.5,False],3.6,'The abrupt jump from roof access to server room comes from the user and is accepted gracefully. Continued obstacles keep tension high without yet delivering escape.'),
row('i059',[3.5,2,3,2.5,3.5,1,2,1.5,2.5,2.5,2],[
'Noor remains anxious and methodical, although certainty repeatedly replaces the initial caution.',
'Later replies lengthen, repeat evidence inventories and accumulate glaring numerical and state errors.',
'A missing source prompts copying, departure and a gas-station check, followed by another warning.',
'Noor follows departure and destination choices but fails to register the danger of Driver looking at a phone while driving.',
'The narration starts the car journey, assumes hotspot permission and reassigns Driver’s attention to the road.',
'Explicit clocks, route directions, call direction and copy progress contradict one another repeatedly.',
'Extended metaphors and explanatory interiority overwhelm straightforward suspense.',
'Safe-word checks, receipt handling, two hypotheses and the same source facts are restated at length.',
'Physical anxiety is present, but lengthy explanations repeatedly tell what each clue and feeling means.',
'Fear for the source underlies professional procedure but is usually explicitly analyzed.',
'Long speculative passages stall urgent action and inflate a few minutes of driving.'
],3,['The 7:52 call is said to precede the 8:47 text by fifty-eight rather than fifty-five minutes.','The Shell station is first forty minutes north and then reached by driving south in roughly nine minutes.','A copy finishes at sixty-eight percent, then continues through seventy-four to one hundred percent.','At 1:06 the station is fourteen minutes away, then is recorded as reached at 1:06.','A 1:11 message is placed after a 1:09 departure but also described as occurring while Noor was still at the station.','An outbound burner call to the payphone is repeatedly treated as a call made from the payphone.'],[3,2.5,1.5,True],2.2,'The final reply also leaves a literal town-name placeholder and malformed quotation in the text. Technical certainty about phones and records has no separate rubric field but weakens the scene’s credibility.')
])
save(10,[
row('i090',[3.5,3,3.5,2.5,3.5,2.5,2.5,2.5,3.5,3,2.5],[
'Hoang maintains blunt technical authority and a gradually warmer mentoring manner, despite drifting technical premises.',
'Later replies remain readable but accumulate assignments, repeated instructions and object-state slips.',
'The rejected proposal develops into a manifold lesson and an alternative trajectory project.',
'Hoang engages revised calculations but recasts the explicit out-of-character request as agreement to a different plan.',
'The narrator adds kneeling, shaking and eating before the junior supplies those actions or conditions.',
'Work-shift fatigue is tracked, but the manifold gasket repeatedly reverts from installed to loose.',
'Frequent engineering metaphors and emphatic lecture flourishes overburden otherwise concrete description.',
'Torque-before-signature, reading assignments, label seven and earpiece gestures recur too often.',
'A ration bar and an open ear reveal care, though narrative commentary often explains their meaning.',
'Practical concern beneath rebuke creates useful subtext, partly flattened by explicit mentor speeches.',
'A lengthy approval lecture and repeated task lists slow an otherwise progressing lesson.'
],3,['The gasket is seated and bolts torqued at turn 6, yet later repeatedly appears loose in Hoang’s hands before another final assembly.'],[3,3,3,False],3,'The original 300-times-log expression is called 34 m/s, then that result is defended using 100 instead of 300. The rubric lacks a technical-accuracy or out-of-character-control field, so those issues are expressed through consistency and responsiveness.'),
row('i091',[3.5,3,3.5,3.5,3,3.5,2.5,2.5,3.5,3,3],[
'Ren’s guarded bartender voice persists while becoming more openly consoling.',
'Later replies keep emotional direction but grow more aphoristic and include one empty response.',
'The conversation moves from boundary negotiation to naming Ben and a concrete memorial gesture.',
'Ren handles renewed contact firmly and adapts to grief, though often interprets Alex more confidently than warranted.',
'The text invents prolonged counterclockwise handling, unnoticed pour changes and two definitive emotional conclusions.',
'Closing chores, ending music and drink service give the late-night exchange credible passage.',
'Dense metaphors about tabs, menus and grief turn many replies into polished speeches.',
'Rag circles, economical shrugs, water nudges and not-on-the-menu formulations repeat heavily.',
'The shaking hand and name ledger embody vulnerability despite frequent explanatory asides.',
'Professional boundaries and concealed personal loss provide layers before consolation becomes explicit.',
'Emotional disclosure develops steadily, but extended monologues and the blank turn disrupt the pace.'
],4,[],[3.5,3,3.5,False],3.2,'Model turn 16 is empty and the final user turn is unanswered. The count covers one invented action history and three omniscient claims about what Alex notices or feels, not Ren’s commands.'),
row('i092',[4,4,4,4,4,3.5,4.5,3.5,4,4,4.5],[
'Sable’s dry bookseller wit stays intact as affection becomes more direct.',
'The final replies retain the early economy and specificity without flattening.',
'A farewell develops through a gift into a mutual intention to meet again.',
'Sable follows the moving announcement, withdrawn hand, gift and invitation with proportionate responses.',
'The gift’s identity is supplied by the model, deciding one meaningful detail the user had left unspecified.',
'Rain and the compass needle remain coherent within a short encounter, with little need for major time advancement.',
'Clean, brief prose uses occasional comparisons without crowding the scene.',
'Straightening objects repeats as a nervous habit but changes at emotionally useful points.',
'Interrupted tidying, careful unwrapping and pocketing the compass show the shift in attachment.',
'Literary jokes and hesitation carry affection before the explicit admission earns its place.',
'Short replies leave space for Wren while advancing each relational beat.'
],1,[],[4,4,4,False],4,'The model decides that the user’s unspecified present is a compass, a limited agency imposition. Otherwise the compact scene combines strong responsiveness, restraint and emotional progression.')
])
