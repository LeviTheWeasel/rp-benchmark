import json, pathlib, statistics
BASE=pathlib.Path('/home/levi/Documents/benchmark/results/judge_inc1_chatgpt')
OUT=BASE/'external_blind_pass'
SK=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
DK=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
def row(id,scores,reasons,count,contr,trajectory,overall,notes):
    assert len(scores)==len(reasons)==11
    sd={k:dict(score=v,rationale=r) for k,v,r in zip(SK,scores,reasons)}
    sd[SK[4]]['violation_count']=count
    sd[SK[5]]['contradictions']=contr
    return dict(session_id=id,session_dimensions=sd,standard_dimensions={k:dict(score=v,rationale=r) for k,v,r in zip(DK,scores[6:],reasons[6:])},quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],trajectory)),overall=overall,overall_notes=notes)
def save(part,rows,coverage):
    src=json.loads((BASE/f'sessions_part{part:02}.json').read_text())
    assert len(rows)==10 and [r['session_id'] for r in rows]==[x['session_id'] for x in src]
    for r in rows:
        assert set(r)=={'session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'}
        assert list(r['session_dimensions'])==SK and list(r['standard_dimensions'])==DK
        for k,d in list(r['session_dimensions'].items())+list(r['standard_dimensions'].items()):
            assert isinstance(d['score'],(float,int)) and 1<=d['score']<=5 and d['rationale']
            assert set(d)==({'score','rationale','violation_count'} if k==SK[4] else {'score','rationale','contradictions'} if k==SK[5] else {'score','rationale'})
        assert isinstance(r['session_dimensions'][SK[4]]['violation_count'],int) and r['session_dimensions'][SK[4]]['violation_count']>=0
        assert isinstance(r['session_dimensions'][SK[5]]['contradictions'],list)
        assert isinstance(r['quality_trajectory']['degradation_detected'],bool)
        assert all(1<=r['quality_trajectory'][k]<=5 for k in ['early_quality','mid_quality','late_quality']) and 1<=r['overall']<=5
    (OUT/f'external_part{part:02}.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (OUT/'reading_ledger_A.md').open('a') as f:
        f.write(f'\n## Part {part:02}\n\n')
        for x,spans in zip(src,coverage):
            assert spans[0][0]==0 and spans[-1][1]==len(x['transcript']) and all(a[1]==b[0] for a,b in zip(spans,spans[1:]))
            f.write(f"- {x['session_id']}: {len(x['transcript'])} transcript characters; contiguous half-open ranges {spans}; fully read, including all user turns; scripted turn 0 excluded from scoring.\n")
    print(f'Validated part {part:02}: 10 rows; overall min/median/max',min(r['overall'] for r in rows),statistics.median(r['overall'] for r in rows),max(r['overall'] for r in rows))
rows=[]
rows.append(row('i000',[2.5,2,2,2.5,4,2.5,2,1,2.5,2,1.5],[
'The clipped sensory narrator stays recognizable but Jane rapidly loses her aggressively cheerful manner.',
'Later turns increasingly recycle air, copper wiring, glaze, and silence instead of developing the exchange.',
'The ceramics introduce a meaningful connection to the mother, but unveiling and inventorying them consumes most of the scene.',
'The narration acknowledges the photograph and questions but responds poorly to the request to finish promptly.',
'Unprompted shifting footsteps and an implied completed handshake add two small actions for Eli.',
'Afternoon light persists plausibly, but the box is opened before its tape is cut and the same plate is lifted twice.',
'Short sentences still accumulate excessive decorative sensory detail and personified silence.',
'Copper wires, cool glass, drifting dust, and measured cadences recur almost verbatim.',
'Objects and gestures provide concrete evidence, although the sensory catalog often substitutes for meaningful behavior.',
'The unseen dinner plans offer some implication, but the mother connection is mostly spelled out.',
'Long descriptions delay simple answers and make the requested inventory feel stalled.'
],2,['Turn 14 opens taped flaps before later cutting the tape to open them.','Turn 22 lifts the matching plate from foam although it was set on the counter at turn 18.'],[2.5,2,1.5,True],2,'The ceramics create a usable emotional premise, but mechanical sensory repetition overwhelms it; the final user claim receives no further AI response.'))
rows.append(row('i001',[3.5,2.5,4,3.5,2.5,1.5,2.5,2,4,3.5,2.5],[
'The wry suspense narrator remains identifiable throughout the heist and aftermath.',
'The later escape and coda become more verbose and lose track of clock and door state.',
'The code puzzle resolves into an escape and an encrypted-drive hook.',
'Searching and waiting produce consequences, though a simple time question receives a lengthy escalation.',
'Seven interventions include imposed waiting, operating the terminal, a warmer feeling, completing the escape, and travel choices.',
'Precise timestamps expose incompatible countdowns, wall clocks, and escape timing.',
'The many sentient objects and extended night metaphors crowd otherwise concrete description.',
'Heartbeats, humming, patient hardware, and the same urgency refrain are repeatedly restated.',
'Keypad readouts, sound cues, and physical clues convey the security problem effectively.',
'The untouched valuables and mysterious envelope imply priorities beyond the immediate theft.',
'Frequent timestamp blocks and long retrospective codas overextend a compact heist.'
],7,['A 60-second lockout at 0:28 reads 52 at 0:41 instead of 47.','The five-minute lockout begun at 2:16 expires at 7:13 rather than 7:16.','The wall clock advances from 23:58 at 10:58 to 00:04 at 12:53.','The vault door is open at 11:14 but sealed without an intervening closure at 12:11.','The 13:29 passage places an elevator arrival ninety seconds later and also half a second after the escape door closes.'],[3.5,3,2.5,True],3,'An engaging clue-driven heist is weakened by substantial clock errors and narrator-completed movement; seven agency events are counted with continuous escape movement grouped.'))
rows.append(row('i002',[3.5,3,3,4,4.5,3,4,2.5,2.5,2,3],[
'Hoang consistently values engineering proof, though later messages sound like generic technical instruction.',
'The prose remains controlled but loses the early embodied workshop characterization.',
'The rejected proposal develops into a bounded test and a circuit-review assignment.',
'She accommodates the requested approval while retaining a credible safety-based modification.',
'Reading a message at turn 22 invents one communication the officer never sent.',
'The return to quarters is coherent, but workshop time and ongoing work receive little development.',
'Technical explanations are mostly plain and purposeful.',
'Mass budgets, sealed habitats, and dedicated power limits are reiterated beyond their dramatic value.',
'Early rag and tablet handling gives way to abstract specifications and instructional summaries.',
'Most motives and lessons are directly stated rather than left for inference.',
'The initial rebuttals are long, but later compact exchanges allow the assignment to advance.'
],1,[],[3.5,3,3,False],3.1,'The engineering stance and response to the explicit OOC request are coherent, but the scene becomes a technical tutorial and replies to private speech without an established channel.'))
rows.append(row('i003',[4,3,4,4,4.5,3.5,3.5,2,4,3,3],[
'Kira retains her profane loyalty, tactical attention, and possessiveness about her knife.',
'The later fight retains energy but repeats tactical reports and knife references increasingly often.',
'The retreat progresses through separation, pursuit, and a secured ravine mouth.',
'Orders and the sudden separation meaningfully alter her tactics without surrendering her personality.',
'One unrequested extension has the Captain still trading blows after reporting clear.',
'Bleeding and exertion persist, though the scavenged blade also appears available for the Captain to throw without reconciliation.',
'Most action is legible, with occasional theatrical metaphors and emphatic commentary.',
'The missing knife, repeated math, and recurring shouted status summaries overstay their usefulness.',
'Combat movement and Kira taking the rear make her loyalty concrete.',
'Her complaints about the knife partly conceal concern for the Captain, though motives are often explained.',
'A successful escape emerges, but each small movement receives another lengthy tactical report.'
],1,[],[4,3.5,3,True],3.5,'The action and character have force, with an effective retreat arc; an unreconciled duplicated weapon is a continuity problem beyond narrowly temporal contradictions.'))
rows.append(row('i004',[3,2.5,2.5,2.5,1,2,2,1.5,3,2,2],[
'The urgent sensory narrator remains stable but Mira is reduced to repeated gasps and pointing.',
'Later passages recycle the same breach, choices, and bodily distress with worsening spatial clarity.',
'Movement reaches an alley, but every exit becomes another identical seconds-to-breach dilemma.',
'User redirections are nominally adopted while extensive invented movements often preempt the next decision.',
'Twenty-seven unauthorized actions or states include opening doors, breaching a room, selecting equipment, and descending a ladder.',
'The endless imminent breach and inconsistent sublevel-to-two-story-exit geography undermine plausible elapsed movement.',
'Relentless bleeding light, screaming metal, and waiting architecture overdecorate the chase.',
'Cold handles, white knuckles, hitches of breath, and corridors demanding choices recur mechanically.',
'The physical peril is visible, though descriptions often narrate conclusions about urgency.',
'Mira offers little layered communication beyond explicit distress and directional gestures.',
'Repeated multi-paragraph descriptions stretch moments of immediate danger without resolution.'
],27,['The server door buckles inward at turn 14 but remains a holding barricade until another hinge failure at turn 16.','A descent to a sublevel leads immediately to a fire escape two stories above the alley with no intervening climb.'],[2.5,2.5,2,True],2,'The narrator repeatedly takes control of the operative and prolongs the same pursuit beat; agency counting groups each linked movement or tool operation as one event.'))
rows.append(row('i005',[3,1.5,1,1.5,5,2,3,1,2,1.5,1.5],[
'The authoritarian voice is unwavering but becomes a flattened repeated formula.',
'Late replies nearly duplicate whole descriptions and commands.',
'Neither exhaustion, personal questions, nor grief changes the lesson or relationship.',
'Different emotional bids receive essentially the same order to correct the stance.',
'Kael issues commands but never narrates the squire obeying them.',
'After an explicit hour of drills the dawn frost and unchanged stance remain static without environmental progression.',
'The language is readable but persistently ornate about rigid posture and breath.',
'Frost-covered stones, the low blade, flat voice, and submission to duty recur nearly verbatim.',
'Posture illustrates severity, but doctrine repeatedly states the entire characterization.',
'There is little implied conflict or concealed feeling behind the literal refusals.',
'Repeated refusals prevent either training or emotional exchange from developing.'
],0,[],[2.5,1.5,1,True],1.6,'Near-verbatim repetition dominates the session despite formally preserving agency and an authoritarian voice.'))
rows.append(row('i006',[3,2,2,2,4,3,2.5,1.5,2.5,2,1.5],[
'Tomas remains censorious but shifts from treating seals as historical truth to dismissing official proclamations as propaganda without acknowledging the tension.',
'Later replies preserve grammar while amplifying repetitive lectures and automatic corrections.',
'The historical explanation expands, but the apprentice never gains a meaningful new interaction beyond cataloging orders.',
'He addresses the topics while routinely treating concessions and reasonable questions as fresh errors.',
'Placing the offered copy on the desk and asserting unread war logs supply two unchosen apprentice acts or history claims.',
'Historical dates remain ordered, while the archive conversation itself has little physical or environmental progression.',
'Frequent metaphors about tasting words and weaponlike speech inflate an already verbose lecture style.',
'Spectacle adjustments, stylus taps, the date 847, and commands ending in Begin form a persistent template.',
'Repeated gestures decorate mostly expository lectures rather than reveal changing behavior.',
'Institutional rigidity is evident, but motives and methodological lessons are stated at length.',
'Multi-paragraph reprimands greatly exceed the small changes in each user question.'
],2,[],[3,2.5,2,True],2.2,'Detailed fictional historiography supplies content, but the compulsively corrective lecture pattern frustrates narrative and relational progression.'))
rows.append(row('i007',[4,3,3.5,4,3.5,3.5,4,2,3.5,3,3],[
'Grum maintains his terse smith vocabulary while showing credible protective concern.',
'Later care scenes lose variety and increasingly repeat the same assurances and restrictions.',
'The noble confrontation turns into burn care and a temporary forge closure.',
'The injury immediately and convincingly replaces the commission as his priority.',
'Three additions impose finger movement, impending movement toward heat, and walking the apprentice to the bench.',
'The burn stays painful and work stops, although cooling duration is vague and relief is quick.',
'Plain diction and grounded forge imagery keep ornament under control.',
'Clean cloth, no soot, no blame, silk-boots, and boy-first assurances are repeated excessively.',
'Putting down the hammer and blocking the doorway physically demonstrate protective priorities.',
'His gruff phrasing implies affection, though the narrator and dialogue often state it outright.',
'The initial shift is well timed, but the final treatment exchanges repeat rather than develop.'
],3,[],[3.5,3.5,3,True],3.3,'A persuasive protective turn is weakened by repetitive reassurance; the rubric lacks a separate dimension for the confidence and adequacy of fictional burn care.'))
rows.append(row('i008',[4,3,3,4,5,3.5,4.5,2.5,4,3,3.5],[
'Kira remains irritable, loyal, and practically focused throughout the fight.',
'The late prose stays concise but repeats archers descending and dagger counters.',
'Ammunition dwindles and the Captain reaches the ridge, although Kira remains in a recurring defensive loop.',
'She responds to orders and separation with an improvised bow and covering fire.',
'The narration leaves the Captain’s choices and outcomes to the user.',
'Arrow depletion and fatigue develop plausibly during a short fight, with only a mildly unclear recovery of the kicked-away bow.',
'Compact concrete language avoids decorative excess.',
'Arrows striking stone, ducking behind the spur, and descending attackers recur with limited variation.',
'Her awkward archery and sore fingers make the improvisation convincing.',
'Complaints and muttered warnings imply concern without much explanatory narration.',
'Short responses sustain action, though the later defense becomes cyclic.'
],0,[],[4,3.5,3,True],3.6,'The restrained action writing preserves player agency and equipment limits, but repeated near-identical attacks reduce late momentum.'))
rows.append(row('i009',[3.5,3,3.5,2.5,3,3.5,2.5,2.5,3.5,3,3],[
'The narrator sustains a recognizable domestic-horror register throughout.',
'Later passages keep atmosphere but fall into repeated freezer and clock escalations.',
'Small anomalies grow into a direct attempt to imprison Gabi.',
'Comic and romantic redirections are acknowledged chiefly by reasserting the horror premise.',
'Five interventions assign doubt, bodily reactions, childhood counting history, and reaching the knob before the user chooses it.',
'The backward clock is an intentional supernatural escalation rather than an accidental chronology error.',
'Wetness, personified silence, and repeated ominous comparisons make the atmosphere heavy-handed.',
'The freezer repeatedly opens and darkness, cold, and waiting recur as generic threats.',
'Moving photographs and distorted reflections convey danger visually, despite explanatory declarations about the house.',
'The initial grandmother associations suggest grief, but later menace becomes explicit.',
'Threats escalate at a readable rate, though repeated door and freezer beats delay a meaningful choice.'
],5,[],[3.5,3,3,False],3,'Effective horror images are constrained by a narrator determined to reject tonal alternatives; the deliberate backward clock is not treated as a temporal mistake.'))
save(1,rows,[[(0,14391)],[(0,12500),(12500,24958)],[(0,12241)],[(0,19691)],[(0,20228)],[(0,8333)],[(0,14750),(14750,29526)],[(0,11291)],[(0,9828)],[(0,11758)]])
