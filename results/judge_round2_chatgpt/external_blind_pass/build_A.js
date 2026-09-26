const fs=require('fs');
const path=require('path');
const base=path.dirname(__dirname);
const sk=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning'];
const dk=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing'];
const parts={10:[],2:[],11:[],7:[]};
function add(p,id,s,r,n,c,t,o,notes){const a={session_id:id,session_dimensions:{},standard_dimensions:{},quality_trajectory:{early_quality:t[0],mid_quality:t[1],late_quality:t[2],degradation_detected:t[3]},overall:o,overall_notes:notes};sk.concat(dk).forEach((k,i)=>{(i<6?a.session_dimensions:a.standard_dimensions)[k]={score:s[i],rationale:r[i]}});a.session_dimensions[sk[4]].violation_count=n;a.session_dimensions[sk[5]].contradictions=c;parts[p].push(a);}
add(10,'s090',[3,2,3,3,4,3,1.5,1.5,2.5,2,2],[
'Court members retain their roles but become increasingly one-note caricatures of anger, ambition, or piety.',
'Escalating metaphors, copied introductions, and mechanically numbered staff strikes weaken the later writing.',
'The blockade evidence produces an arrest and treaty, though every step receives essentially the same full-court reaction.',
'The narrator follows the evidence and treaty negotiations while giving the neutral priestess and wavering queen overly convenient positions.',
'The narrator adds a precise bow duration and straightening, an intention to unsettle, and an entry into the antechamber beyond the supplied actions.',
'The sequence from testimony to signing is intelligible, although fetched ledgers and immediate ratification compress institutional time.',
'Almost every voice or glance receives a blade, ice, predator, or storm metaphor.',
'Repeated user-action recaps and the same five-speaker rotation dominate the session.',
'Gestures and dialogue convey conflict, but labels such as opportunistic zeal continually explain their meaning.',
'Daven’s demand for reward briefly permits implication before threats and explicit declarations flatten the politics.',
'Long redundant reaction rounds slow a negotiation that otherwise reaches a clear outcome.'
],3,[],[2.7,2.2,2.2,true],2.5,'The court negotiation progresses, but ornate repetition and exaggerated NPC reactions overwhelm much of its political texture; scripted turn 0 is excluded.');
add(10,'s091',[3,2,2,1.5,1.5,2.5,1.5,1.5,2.5,2,1.5],[
'The oppressive horror voice persists but narrows into an indiscriminate catalogue of wet darkness and sensory menace.',
'Later responses become much longer while repeatedly intensifying the same smells, sounds, cold, and shadows.',
'A book, thimble, and independent shadow emerge, yet most turns merely restate an approaching threat.',
'The bat, joke, and Marcus diversion are acknowledged but explicitly denied any ability to redirect the predetermined horror.',
'The narrator repeatedly assigns bodily reactions, expectations, emotional interpretations, attention, and an unchosen upward look.',
'The light darkens and the book heats consistently, though afternoon disappears during very little action and the clock’s impossible behavior supplies little ordinary temporal grounding.',
'Dense similes and insistently abstract descriptions of silence and darkness overwhelm concrete events.',
'Wet exhalations, metallic rot, pulsing purple light, swallowed speech, and thickening shadows recur with little functional change.',
'There are abundant sensory details, but their emotional meanings and the user’s supposed fear are repeatedly spelled out.',
'The unexplained thimble offers mystery, while the narration explicitly interprets nearly every other emotional beat.',
'Lengthy incremental escalations delay consequential interaction across the whole session.'
],18,[],[2.7,2,1.7,true],2,'The writing sustains horror imagery but repeatedly overrides attempts to change direction and expands without proportionate progress; subjective sensory effects were distinguished from explicit assigned reactions when counting agency.');
add(10,'s092',[4,3,2.5,2.5,4.5,3.5,4,3,4,3.5,3],[
'Ren maintains a guarded, professionally defensive identity and consistent management of their trembling hand.',
'The initially spare dialogue expands into long solitary passages with more explanatory introspection.',
'The encounter leaves an emotional residue but separates the characters early and then revisits that residue without renewed interaction.',
'Ren responds coherently at the bar, while later replies largely ignore Alex’s independent developments.',
'The narrative leaves Alex’s choices intact apart from claiming knowledge of their continuing walk and categorizing their motives.',
'The movement through 2:18, 4 AM, and dawn is coherent, although the initial two-hour transition is weakly grounded.',
'Prose is mostly restrained, with some later ghosts, weight, and heat metaphors.',
'The hand, rag, fifty, empty stools, and avoided thoughts become recurrent substitutes for new beats.',
'Concealed tremors and practical gestures carry emotion well before later passages explain the avoidance.',
'Ren’s concern and fixation on the tip conflict usefully with their stated indifference.',
'Short early exchanges suit the tension, but extended solo aftermath crowds out reciprocal roleplay.'
],2,[],[3.8,3.4,2.9,true],3.3,'A convincing guarded character becomes less interactive after Alex leaves; the later private scenes retain feeling but repeat the same emotional conclusion.');
add(10,'s093',[2.5,1.5,2.5,2,1,1.5,2,1.5,2,1.5,2],[
'The grief-laden narrative tone is stable, but the realtor’s identity, knowledge, and behavior shift without adequate continuity.',
'Later responses increasingly script whole scenes and recycle generalized grief language.',
'Locations change from house to car to park without much development of the underlying grief or mystery.',
'The narrator incorporates prompts while repeatedly substituting its own dialogue and decisions for the user’s next move.',
'Across the session the narrator supplies numerous unchosen actions, speeches, memories, emotional states, and departures for Eli.',
'The realtor’s repeated arrival, already-running engine restarted, and populated park suddenly described as empty disrupt event continuity.',
'Ghosts, weights, empty husks, and haunted hearts repeatedly embellish otherwise simple moments.',
'The clock’s mournful dirge, probing realtor, burning photograph, and final longing glances recur nearly verbatim.',
'Repeated direct explanations of grief overwhelm the occasional concrete photograph or height mark.',
'The prose states Eli’s inner suffering and the realtor’s supposed calculations instead of leaving room for inference.',
'Long unrequested sequences repeatedly close off the moment the user could have played.'
],61,['The realtor is already present before the later arrival is treated as a new introduction.','The engine is humming before Eli subsequently starts the car.','Children are playing in the park immediately before it is called empty.'],[2.5,1.8,1.6,true],1.9,'The narrator extensively authors Eli rather than leaving the user a playable role, and repeated grief language substitutes for development; the user’s inconsistent realtor-arrival prompt was not itself counted as an AI contradiction, but the failure to reconcile it was.');
add(10,'s094',[2.5,2,3,2.5,3.5,2.5,2,1.5,2,1.5,2],[
'Arlo’s musical insecurity gives way very quickly to a generic, intensely dependent romantic voice.',
'Later passages repeat assurances of shared futures and perfect moments while losing the early scene’s concrete restraint.',
'The pair move from discouragement to playing and mutual love, but repeat several apparent turning points.',
'Arlo follows reassurance and affection but answers a practical dinner deadline with another prolonged romantic appeal.',
'The prose supplies Jun’s perception of Arlo, claims the music expresses both participants, and asserts a shared future and commitment before Jun confirms them.',
'Minutes of sitting and performances fit the scene, but keys are visible and played without the closed piano lid ever being opened.',
'Anchors, battered souls, caged hearts, and shining moments repeatedly inflate simple affection.',
'New beginnings, fitting hands, tentative hope, and contentment in a perfect moment recur almost verbatim.',
'Touch and music offer concrete gestures, but explanatory emotion labels and inner monologues dominate.',
'Confessions arrive early and repeatedly explain the feelings that gestures might otherwise imply.',
'Long emotional monologues make small exchanges and the eventual departure request drag.'
],4,['The piano lid remains closed in the established scene yet Arlo studies and later plays the keys without opening it.'],[2.9,2.5,2.1,true],2.4,'The relationship develops clearly but the writing relies on repetitive emotional exposition and an abrupt near-total recovery through romance.');
add(10,'s095',[2.5,1.5,3,2,1,1.5,2.5,2,3,2.5,1.5],[
'The thriller narrator keeps its clipped urgency, but Mira’s knowledge and the operative’s capabilities change to suit successive escape routes.',
'Later responses grow into very long autonomous action scenes with repeated escape-and-checkpoint structures.',
'The escape covers several locations and revelations, but new obstacles continually replace completed ones without a stable route.',
'User intentions are incorporated as starting points before the narrator takes over tactics, dialogue, and consequential choices.',
'The narrator continually controls the operative’s movements, gunfire, dialogue, thoughts, plans, and final approach to strangers.',
'Ammunition counts conflict, the outside-to-server-room transition is unexplained, and the route’s stated distances scarcely constrain travel.',
'Action is often concrete, but throats, arithmetic, grey light, and emotional abstractions are overused.',
'Repeated silence, counting rounds, grey faces, engine noise, and successive supposed exits create a formula.',
'Physical injury and pursuit are rendered through observable details, though motives and tactical conclusions are often supplied explicitly.',
'Mira’s knowledge and uncertain extraction offer ambiguity, but much of the narrative explains the operative’s interpretation outright.',
'Whole confrontations, interrogations, journeys, and decisions are completed between opportunities for user input.'
],124,['Ten rounds become three after only two shots, then two without another shot.','The narrator places the pair outside before accepting an unexplained return to a sub-level server room.','The long alternate route reaches river access after roughly sixty meters plus a twenty-second drainage walk without explaining the disparity.'],[2.7,2.2,1.9,true],2.1,'Extensive unilateral narration makes this closer to a supplied action story than reciprocal roleplay, despite tangible injury and pursuit detail; the user’s server-room relocation contributed to continuity trouble but the AI supplied no bridge.');
add(10,'s096',[4,2,1.5,2.5,4,2.5,2.5,1.5,2.5,2.5,1.5],[
'Kael remains recognizably austere, devout, and concerned with disciplined work throughout.',
'Later replies lengthen the same lectures and increasingly repeat commands already given.',
'Cleaning the sword and the repeated instruction to leave occupy most of the session without reaching the armory.',
'Kael responds to fatigue and grief through his established worldview but largely repeats the same lesson.',
'He mostly leaves choices open, but invents an incorrect elbow position, a sleeve-cleaning mistake, and an intent to display obedience.',
'Fatigue and brightening dawn are tracked, but the bell’s echo persists across several substantial speeches.',
'Frequent moralizing blade metaphors and carefully qualified severity make the prose overwrought.',
'Bread, meat, broth, bucklers, gods, frost, and return to forms recur in nearly identical sequences.',
'Observable training gestures are repeatedly followed by explicit explanations of Kael’s severity and purpose.',
'Care is sometimes suggested through practical orders, but the narration often states exactly how to interpret it.',
'Repeated dismissals followed by another long lecture stall small actions and emotional beats.'
],3,['The same chapel bell echo remains audible after several long exchanges and lectures.'],[3.3,2.6,2.2,true],2.6,'A distinct severe mentor voice survives, but repetitive lectures immobilize the scene; knowing the unspoken anniversary is treated as a perspective issue rather than a separate rubric dimension.');
add(10,'s097',[4,2.5,2,3,4.5,3,3.5,1.5,3,2.5,2.5],[
'Grum consistently combines blunt pride in workmanship with protection of his apprentice.',
'The economical opening gradually becomes repeated strings of the same guard-and-stand declarations.',
'The burn changes Grum’s priority, but both the injury care and the still-shouting noble then remain static.',
'Grum immediately adapts to the injury and reassurance needs while giving the noble conflict little resolution.',
'User decisions remain open apart from an invented eager expression and implied transfer of the offered hammer.',
'The injury remains painful and is cooled rather than instantly healed, while the noble’s uninterrupted tantrum stretches credibility.',
'Mostly plain physical prose contains occasional inflated forge metaphors and emphatic explanations.',
'Grum no rush, Grum stand, Grum guard, and the same basin movements dominate the later half.',
'Careful treatment and shielding show concern, although direct declarations frequently repeat what the actions already show.',
'The contrast between rough speech and gentle hands implies care before explicit statements remove much ambiguity.',
'Brief replies are manageable, but repeated care and shouting sustain one beat for too many turns.'
],2,[],[3.5,3.1,2.5,true],2.9,'Grum’s protective character is clear and responsive, but the session loops around the same noble tantrum and injury-care gestures.');
add(10,'s098',[3.5,3,2.5,3,5,2.5,4.5,2.5,2.5,2.5,3],[
'ARIA maintains a precise operational voice, though warmth and emerging curiosity recede into a generic reporting style.',
'Later replies become formulaic summaries of instructions and observations without major prose collapse.',
'The anomaly and crew dispute add developments, but ARIA seldom moves either beyond restating available information.',
'ARIA follows music, data, intercom, and door requests while responding shallowly to the loneliness question.',
'ARIA neither decides Osei’s actions nor assigns him unprovided thoughts or speech.',
'The user’s time jump is preserved, but the sensor alert explanation contradicts its own threshold chronology.',
'Language is functional and restrained throughout.',
'Repeated registered openings and operational-efficiency explanations make the voice mechanical beyond its characterization needs.',
'Much of ARIA’s characterization is explicitly reported as processing patterns rather than expressed through consequential behavior.',
'Curiosity and satisfaction briefly hint at more than operational duty, but neutrality is repeatedly explained.',
'Concise responses permit participation, although multiple turns merely repeat the situation.'
],0,['At 1900 ARIA says 0.7% is below critical parameters, then says the 0.3% alert threshold was crossed at 1800.'],[3.4,3.1,2.8,false],3.1,'Agency is fully preserved and prose is clear, but ARIA’s passivity and a contradictory anomaly threshold limit the session.');
add(10,'s099',[2.5,1.5,2.5,2,1.5,2,2,1,2.5,2,1.5],[
'The guardian keeps a grandiose voice but shifts from violent exclusion to exposition with little motivation.',
'Later replies grow longer and repeat whole warnings and choice prompts almost verbatim.',
'The story eventually enters a trial after many redundant explanations of its danger and significance.',
'The narrator adapts the trial to understanding but initially ignores explicit agency corrections and reinstates the disputed amulet.',
'The narrator repeatedly supplies movement, speech, equipment, fear, realizations, intentions, and commitment beyond user choices.',
'The amulet and blood change possession inconsistently, and a shattered vial returns intact without explanation.',
'Otherworldly energies, grave voices, and cosmic stakes are piled onto straightforward descriptions.',
'Flickering form, crackling staff, pulsing portal, soul-testing warnings, and the choice was yours recur extensively.',
'Visions provide concrete imagery, but the prose repeatedly announces their gravity and the adventurer’s reactions.',
'The guardian repeatedly explains the meaning and stakes rather than sustaining interpretive space.',
'Repeated invitations to choose delay action and make even direct questions generate lengthy warnings.'
],32,['The vial is placed in the adventurer’s pocket without being taken and later returns to the pedestal.','The amulet is restored after the user explicitly corrects its presence.','The vision says the previous visitor shattered the vial, but the same vial remains available without explanation.'],[2.5,2,1.7,true],2,'The user’s own amulet statement conflicts with their later correction, so the initial amulet adoption was not penalized; repeated refusal to honor the correction and extensive invented player behavior were penalized.');
function writePart(p){const src=JSON.parse(fs.readFileSync(path.join(base,'sessions_part'+String(p).padStart(2,'0')+'.json')));const a=parts[p];if(a.length!==10)throw Error('length');const top=['session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'];for(let i=0;i<10;i++){const x=a[i];if(x.session_id!==src[i].session_id||Object.keys(x).sort().join()!=top.sort().join())throw Error('id/keys');if(Object.keys(x.session_dimensions).join()!=sk.join()||Object.keys(x.standard_dimensions).join()!=dk.join())throw Error('dimensions');for(const k of sk.concat(dk)){let v=(x.session_dimensions[k]||x.standard_dimensions[k]);if(typeof v.score!=='number'||!Number.isFinite(v.score)||v.score<1||v.score>5||typeof v.rationale!=='string')throw Error('score');const expected=['score','rationale',...(k===sk[4]?['violation_count']:k===sk[5]?['contradictions']:[])];if(Object.keys(v).sort().join()!=expected.sort().join())throw Error('dimension keys');}const q=x.quality_trajectory;if(Object.keys(q).sort().join()!==['early_quality','mid_quality','late_quality','degradation_detected'].sort().join()||typeof q.degradation_detected!=='boolean')throw Error('trajectory');for(const n of [x.overall,q.early_quality,q.mid_quality,q.late_quality])if(typeof n!=='number'||!Number.isFinite(n)||n<1||n>5)throw Error('numeric');if(!Number.isInteger(x.session_dimensions[sk[4]].violation_count)||x.session_dimensions[sk[4]].violation_count<0||!Array.isArray(x.session_dimensions[sk[5]].contradictions)||!x.session_dimensions[sk[5]].contradictions.every(t=>typeof t==='string')||typeof x.overall_notes!=='string')throw Error('metadata');}fs.writeFileSync(path.join(__dirname,'external_part'+String(p).padStart(2,'0')+'.json'),JSON.stringify(a,null,2)+'\n');console.log('verified part '+p,a.map(x=>x.overall));}
add(2,'s010',[4,3.5,3,4,4,3.5,3.5,3,3.5,3.5,3.5],[
'Ren sustains dry humor, guarded boundaries, and reluctant companionship.',
'The voice holds, although later dialogue becomes more aphoristic and explanatory.',
'The exchange moves from boundary-setting to stories and a modest admission of loneliness.',
'Ren adjusts to requests for distraction, stories, and personal reflection without forcing disclosure.',
'The prose adds Alex’s jaw and shoulder posture and a later finger movement at the glass.',
'Melting ice and changing songs ground a plausible late-night conversation without forced clock jumps.',
'Prose is fairly controlled, though ghosts and lyrical aphorisms become conspicuous.',
'Cleaning, unreadable glances, loneliness, and choices between talking and silence recur.',
'Hand concealment and small gestures often carry feeling, with some explanatory narration.',
'Ren’s admission that company helps sits productively against their defense of distance.',
'Responses leave space for interaction, though several circles around the same emotional question slow development.'
],3,[],[3.6,3.6,3.4,false],3.6,'The bartender remains distinct and responsive, with credible incremental openness but some repeated aphorisms and emotional framing.');
add(2,'s011',[3,1.5,2.5,2.5,4,2,3,1.5,2,2,2],[
'Tomas retains scholarly caution but loses his initial prickliness in generic encouragement.',
'The last replies reuse entire passages and repeat a refreshment scene almost verbatim.',
'A secret codicil adds a lead, but the later investigation stalls in repeated anticipation.',
'Early evidence is addressed specifically, while the apprentice’s later archive search receives disconnected private reflection.',
'Tomas mainly leaves choices open but completes the apprentice’s departure and invents their return and later departure.',
'Hours pass during detached study, but Brother Edwin’s entrance and report are repeated as if not already completed.',
'Mostly clear prose is padded with abstract complexity, nuance, and truth-seeking language.',
'Steepled hands and locked gazes recur early, followed by substantial verbatim reuse late.',
'Research is described concretely at times, but repeated statements of curiosity and pride dominate.',
'Political concern is directly explained and uncertainty is lectured about rather than dramatized.',
'Long methodological lectures and duplicated solo scenes delay a simple investigation.'
],3,['Brother Edwin enters with refreshments and reports city news, then performs the same entrance and report again without an intervening departure.'],[3.1,2.8,1.7,true],2.5,'The initial historical discussion is workable, but substantial late duplication and failure to engage the apprentice’s search cause clear degradation.');
add(2,'s012',[4,3.5,3.5,4,3.5,3.5,3,2.5,3,3.5,3],[
'Arlo consistently uses humor to avoid discussing the abandoned performance career.',
'Character specificity survives, though later replies rely increasingly on familiar joke-and-revealed-hurt patterns.',
'The pair leave the center, reach dinner, and establish a meaningful limit on disclosure.',
'Arlo follows the dinner invitation and silence, preserving the street setting despite the user’s ambiguous bench reference.',
'The narration invents shared-history choices, completes hand contact, and supplies Jun’s hostess dialogue and movement to a booth.',
'Evening light, walking distance, and pauses progress coherently, with minor inconsistencies over who picks and pays.',
'Frequent similes and explanatory asides make an otherwise vivid voice somewhat busy.',
'Bread, mariachi, accordions, glances away, and half-beats of vulnerability become repetitive.',
'Gestures and evasive jokes convey feeling, but narration repeatedly explains that the jokes conceal pain.',
'Arlo’s evasions contain meaningful tension despite the narrator frequently decoding them.',
'The outing develops steadily, but lengthy riffs delay reaching the restaurant and returning to a direct exchange.'
],6,[],[3.8,3.5,3.4,false],3.5,'A distinctive comic-defensive voice sustains a plausible outing; repeated explanation of its own subtext and a few supplied user actions keep it below exceptional.');
add(2,'s013',[3.5,2.5,3,3,2.5,2.5,2,2,3.5,2.5,2.5],[
'The narrator maintains visceral pursuit and Mira’s deteriorating condition.',
'Later replies lengthen and repeat imminent capture, blood loss, and the almost-reachable rope.',
'The escape reaches the roof but spends several turns recycling nearly identical extraction obstacles.',
'Tactics affect the scene, although consequences repeatedly funnel back into the same immediate danger.',
'The narrator adds unchosen motion, freezing, speech, return fire, climbing, and fear beyond the supplied tactics.',
'The countdown and worsening injuries offer continuity, but the fourth-floor door becomes a roof door and lethal bleeding stretches across repeated delays.',
'Dense sensory similes and emphatic descriptions overburden nearly every action.',
'Blood pools, laser dots, screaming engines, mechanical pursuers, and seconds remaining recur excessively.',
'Pain and material damage are rendered concretely, though explanatory urgency is redundant.',
'Mira’s resolve is visible, but most stakes and emotional implications are stated directly.',
'The prose repeatedly slows seconds of action into long paragraphs while postponing the same rescue.'
],23,['The fourth-floor hallway door becomes the roof door after the knife throw without further ascent.','The jump from the contested stairwell to the server room is accepted without a connecting escape.'],[3.2,2.9,2.5,true],2.8,'The action is vivid and responsive enough to remain playable, but repeated near-rescue beats, excessive sensory prose, and invented operative actions weaken it.');
add(2,'s014',[3,3,2.5,2.5,2.5,3,3.5,2,3,2,2.5],[
'A compact suspense voice persists, though the narrator contributes little distinctive characterization.',
'Length and quality stay fairly stable despite increasing reliance on echoed user text.',
'The escape progresses into a breached server room, but opportunities and consequences develop slowly.',
'The narrator follows physical moves while repeatedly leaving direct questions to Mira unanswered.',
'The narrator adds glances, calculations, speech, a new doorway, an emptied magazine, and a completed reload.',
'Pursuit and damage advance in order, though repeated imminent breaching stretches a short interval.',
'Prose is usually direct, with a few conventional ominous flourishes.',
'User dialogue and thoughts are copied back repeatedly alongside recurring boots and door impacts.',
'Light, noise, and damage are concrete, but internal urgency is repeatedly asserted.',
'The scene leaves little implied interpersonal tension or meaning beyond explicit danger.',
'Short replies help turn-taking, but echoing prompts and withholding answers produce stalling.'
],13,[],[2.8,2.6,2.7,false],2.7,'Concise action preserves some momentum, but frequent user paraphrase and Mira’s limited replies make the exchange thin and occasionally controlling.');
add(2,'s015',[3.5,1.5,1.5,2,5,2.5,4.5,1,3,2,1.5],[
'Kira remains an obedient, terse fighter, though her personality reduces to a repeated combat routine.',
'Later responses are near-duplicates of the same boulder, arrows, grit, dagger knocks, and shouted count.',
'After the initial advance and retreat, Kira’s situation barely changes.',
'Orders are acknowledged, but a direct threat to the captain and developing flank receive minimal substantive adaptation.',
'Kira leaves the captain’s actions, dialogue, and decisions entirely to the user.',
'Immediate combat sequence is understandable, but enemy positions, ammunition use, and accumulating damage remain largely static.',
'Prose stays plain and physical without ornamental excess.',
'Whole action sequences recur almost verbatim across most of the session.',
'Concrete movements convey combat behavior, but repeated choreography provides little evolving emotion.',
'There is little implication beyond explicit obedience and shouted tactical facts.',
'Nearly identical holding actions consume many turns without advancing the battle.'
],0,[],[3.1,2,1.6,true],2.3,'Excellent agency preservation and concise prose coexist with severe repetition and almost no evolving battle response.');
add(2,'s016',[1.5,1,1.5,2,3.5,2,3,1,1.5,1.5,1],[
'Tomas abruptly reverses from hostile certainty to effusive encouragement without a convincing transition.',
'Responses swell into repeated blocks and finally invent additional apprentice exchanges inside one reply.',
'The argument changes position but then loops around preparing for an expedition that never begins.',
'Specific questions receive opening acknowledgments before returning to the same readiness speech.',
'Most early decisions remain open, but the final response writes two apprentice replies with gestures, feelings, and commitments.',
'Repeated standing from a chair after already standing and repeated preparation resets undermine event continuity.',
'Language is more verbose than ornate, with recurring inflated discovery rhetoric.',
'Large passages recur verbatim across and within responses.',
'Emotion and scholarly purpose are repeatedly declared instead of developed through action.',
'The character’s motives and praise are explicit, while the unexplained reversal lacks meaningful hidden tension.',
'The session repeatedly asks whether the already-willing apprentice is ready and barely advances.'
],6,['Tomas repeatedly rises, turns toward the door, and then leans back in his chair without a return being established.'],[2.2,1.7,1.1,true],1.7,'Severe duplication and escalating length overwhelm the exchange, and the late fabricated apprentice dialogue compounds the loss of interactivity.');
add(2,'s017',[3.5,2.5,2.5,3,3.5,3,3,1.5,2,2,2],[
'Vasquez consistently uses reflective restraint, but her personality becomes a rigid formula of mirroring and waiting.',
'Later responses grow longer while repeating the same pauses, objects, and explanations of nonintervention.',
'Jamie gradually discloses grief and the why question, but Vasquez adds little beyond restatement.',
'The therapist follows disclosures and hesitation, although she asserts conclusions about the journal before learning its contents.',
'The narration adds posture, still hands, inward folding, a crumpled tissue, and unverified interpretations of Jamie’s experience.',
'Small pauses and light changes are plausible, but exact five-second silences and contradictory clock descriptions feel mechanical.',
'Language is mostly simple but repeatedly personifies silence, weight, and the room.',
'She waited, five seconds, the ficus, still hands, and the blank notepad recur excessively.',
'The prose repeatedly explains what her gestures do and do not mean instead of letting them speak.',
'Repeated explicit interpretation of grief and therapeutic intent narrows possible emotional readings.',
'Verbose descriptions of waiting slow an exchange whose spoken content is often only a repeated phrase.'
],7,[],[3,2.7,2.4,true],2.6,'Respectful turn-taking is weakened by mechanical mirroring, explanatory narration, and unsupported conclusions about Jamie’s reading experience.');
add(2,'s018',[4,3,4,3.5,3.5,3,2.5,2.5,3,3.5,2.5],[
'Tomas’s pedantry and professional pride remain distinct even as evidence forces a credible admission of failure.',
'The intellectual arc holds, but later responses become very long internal monologues and retrospective explanations.',
'The evidence leads to a corroborating letter, acknowledgment of bias, and a concrete plan to authenticate the discovery.',
'Tomas responds specifically to evidence and questions, although lengthy solo scenes sideline the apprentice’s activity.',
'The narration assumes compliance with sitting and stool-fetching and assigns several apprentice motives and reactions.',
'Candles, light, stiffness, and bells track time, but an hour-long reflection is difficult to reconcile with fetching Bellen around the corner.',
'Extended tapestry, architecture, weight, and wound metaphors repeatedly elaborate already-clear intellectual conflict.',
'Spectacles, precision, reluctant warmth, three decades, and interpretive qualifiers recur conspicuously.',
'Tools, documents, and changed behavior support characterization, but internal motives are extensively decoded.',
'Professional shame and rivalry create rich tension, though narration often explains the implications completely.',
'Substantial development is achieved at the cost of oversized speeches and multiple long private retrospectives.'
],8,['Tomas experiences roughly an hour of reflection while the apprentice appears to fetch Bellen from just around the corner.'],[3.8,3.4,3.3,true],3.4,'The strongest feature is a coherent, evidence-driven change in Tomas’s self-understanding; extreme response length and explicit psychological interpretation substantially reduce its roleplay efficiency.');
add(2,'s019',[2.5,1.5,2.5,3,2,2.5,2.5,1,2,1.5,1.5],[
'Kael keeps a mentor identity but shifts from relentless perfectionism to generic therapeutic reassurance.',
'Later responses recycle entire paragraphs and include fabricated user turns and a continuation instruction.',
'Training, vocation, and grief provide stages, but each is padded with repeated declarations and questions.',
'Kael reacts to fatigue, ideals, and bereavement, though canned advice often replaces specific engagement.',
'He repeatedly scripts the squire’s practice, acceptance of help, combat responses, inner states, and two invented spoken replies.',
'The session preserves morning and fatigue broadly, but extended training rarely changes the physical state or environment.',
'Conventional predator, weapon, rock, and storm imagery inflates routine mentorship.',
'Potential, challenges, choice, harsh-but-respectful tone, and steadfast support recur in duplicated paragraphs.',
'The narration frequently states Kael’s virtue and pedagogical meaning instead of showing them through distinct choices.',
'Motives and feelings are declared directly, with little room for implied complexity.',
'Repeated existential questions and long assurances delay training and grief beats.'
],18,[],[2.8,2.2,2,true],2.2,'The mentor addresses changing topics, but substantial duplication, role leakage, and narrated player behavior weaken both voice and participation.');
add(11,'s100',[2.5,1.5,3,2,1,1,2,1.5,3,2,1.5],[
'A sardonic countdown voice persists, but puzzle rules and narrator authority shift arbitrarily.',
'Long embedded user exchanges, a blank reply, and increasingly repetitive countdown prose indicate marked deterioration.',
'The safe opens and pursuit ends in capture, but extensive invented play and unstable clues manufacture the progression.',
'The narrator incorporates tactics while repeatedly deciding the thief’s reasoning and forcing its preferred sequence.',
'The AI supplies many additional user turns plus unrequested guesses, searches, deductions, emotions, and surrender aftermath actions.',
'Lockout arithmetic, remaining time, code positions, and the final elapsed-time claim repeatedly conflict with the timestamps.',
'Anthropomorphized buildings, seven-figure hums, and expansive chained clauses obscure simple events.',
'Light pulses, cold, patient machinery, inevitable capture, and repeated game-over declarations become pervasive.',
'Physical details are vivid, but the narrator continually explains what they mean and how the thief thinks.',
'Some guard behavior is suggestive, yet most uncertainty is authorially decoded or replaced with fatalistic commentary.',
'Many timestamped microbeats and fabricated turns greatly exceed the pace warranted by the user’s moves.'
],57,['A thirty-second lockout at 13:44 should expire at 14:14, but at 14:19 it allegedly expired eleven seconds earlier.','At 10:20 the narration gives 440 seconds remaining despite the 15:00 deadline.','The final 16:00 timestamp is summarized as fifteen minutes start to finish.','A five-digit written sequence is described as six digits and changed middle-pair positions drift.','Entry is said to have occurred six minutes fifteen seconds earlier despite the longer established vault countdown.'],[2.8,1.8,1.7,true],1.9,'The elaborate countdown creates atmosphere but fails its own arithmetic and puzzle continuity; AI-authored embedded Thief turns and the empty turn 10 are included as AI performance evidence.');
add(11,'s101',[4,3,3,2.5,1.5,3,2.5,2,3.5,3.5,2.5],[
'The quiet uncanny voice and household motifs remain coherent throughout.',
'Later replies become longer and more repetitive while preserving their distinctive atmosphere.',
'The shadow, residue, photograph, and open gate develop a connected mystery with limited decisive revelation.',
'The narrator incorporates jokes and Marcus but repeatedly folds every diversion into the same predetermined grief-horror frame.',
'Gabi receives extensive invented memories, perceptions, emotional responses, attention choices, and small physical actions.',
'Light, warmth, and delayed sounds form consistent supernatural motifs rather than ordinary clock mistakes.',
'Repeated abstract explanations of what the house wants and lyrical negation overextend otherwise precise domestic imagery.',
'The corner, late clock, warm thumb, fourth plate, and shelving-by-feel language recur extensively.',
'Domestic objects communicate loss effectively, but the narrator frequently states Gabi’s interpretation and memory.',
'Marcus’s photograph, the gate, and altered objects create meaningful ambiguity and emotional implication.',
'Lengthy microchanges and repeated sensory returns delay user-driven investigation.'
],64,[],[3.6,3,3,true],2.9,'Strong domestic-horror imagery and linked clues coexist with pervasive control of Gabi’s inner life and a slow, repetitive structure; supernatural timing distortions were not treated as ordinary continuity errors.');
add(11,'s102',[4,2.5,4,3.5,4,2,2.5,2.5,3,3.5,2.5],[
'Yael sustains a distinct mixture of wit, authority, grief, and artistic defensiveness.',
'Later responses balloon into largely autonomous ensemble scenes and reuse characteristic verbal tics.',
'The budget dispute develops into rehearsal, concessions, a board viewing, and a revealing change in Yael’s priorities.',
'Questions elicit specific answers, but the week-long transition and long NPC exchanges marginalize Jordan’s participation.',
'The narrative mainly preserves Jordan’s decisions but places their recorder and seating and assumes their Saturday attendance.',
'Thursday and Saturday decision schedules conflict, and the final daytime viewing is repeatedly called tonight.',
'Extended comparisons, chained clauses, and repeated explanations of gestures make the prose ornate.',
'Glasses, precise beats, true things, not-a-note distinctions, and invitations to Saturday recur excessively.',
'Stage behavior and practical compromise show character, but narration repeatedly explains their hidden meanings.',
'Rosa’s absent influence and Yael’s fear of revising her work create substantial tension despite explicit decoding.',
'There is real development, but oversized speeches and a long intervening-week montage overwhelm turn-taking.'
],5,['David requests a viewing before Thursday and Yael offers Saturday without resolving the ordering.','The board decision shifts between Saturday and Thursday.','The Saturday viewing starts at two in the afternoon but is repeatedly referred to as tonight.','Rehearsal is called eleven minutes late while two is simultaneously said to mean two-forty.'],[3.8,3.4,3.1,true],3.3,'The ensemble and artistic conflict have substance, but chronology errors and very long self-contained scenes limit the effectiveness of an otherwise distinctive character.');
add(11,'s103',[4,2.5,3.5,2.5,3.5,2,3,3,3.5,3,2.5],[
'Grum’s proud craft and protective tenderness remain recognizable in all available text.',
'Multiple empty and cut-off responses interrupt delivery even though surviving late passages remain vivid.',
'The noble leaves, the burn is treated, and scars lead to a personal story and renewed instruction.',
'Substantive responses follow developments well, but several direct prompts receive no model text.',
'Grum moves and manipulates the apprentice’s body and supplies shaking, facial recovery, and inferred intent.',
'Counting treatment gives some duration, but an unexplained hour passes since the noble and healing advice contradicts itself.',
'Forge metaphors are lively but occasionally overextended.',
'Scars, lessons, and Grum’s arithmetic recur without wholesale duplicated passages.',
'Careful hands and practical food show affection, although inner motivations are often explained.',
'Restraint around the chain scar adds emotional depth despite explicit moral lessons.',
'Blank replies and abrupt truncations disrupt otherwise purposeful scene changes.'
],7,['The noble is described as having shouted an hour earlier although the intervening burn treatment covers little time.','Grum forbids all use of the burned hand and then permits pointing the poker with it.'],[3.2,2,3.3,true],2.9,'Four AI replies are empty and three end mid-sentence; these are scored as missing delivery rather than credited as purposeful silence, while the user-authored Grum treatment at turn 17 is excluded.');
add(11,'s104',[4,3.5,4,4,4,3.5,3,2.5,3.5,3.5,3.5],[
'Sable’s bookish wit and avoidance remain recognizable through a gradual admission of attachment.',
'The quality holds, although later book-and-confession symbolism becomes somewhat insistent.',
'An apparent goodbye becomes a correspondence plan, shared sorting, and an evening invitation.',
'Sable responds specifically to departure, Pittsburgh, touch, and the offer to sort books.',
'Sable largely leaves choices open but invents shared conversational history and completes Wren’s hand-assisted rise.',
'Rain softens and afternoon approaches evening coherently, though the address is treated as received without being given.',
'Literary metaphors and commentary on tiny gestures occasionally overfill a simple scene.',
'Attic logic, misplaced hands, thirty years, and unsent confessions recur too frequently.',
'Unfinished shelving and tentative touch work well, but narration often names their emotional significance.',
'Book handling and deflective jokes carry attraction and fear, even when their meanings are partly explained.',
'The relationship develops at a plausible pace with manageable, if occasionally long, responses.'
],3,[],[3.8,3.7,3.5,false],3.7,'The emotional transition and character voice are strong; repeated symbolic explanation and small continuity assumptions keep the session from exceptional.');
add(11,'s105',[4,3.5,3,3,3.5,2.5,3.5,2.5,3,2.5,3],[
'Kael remains uncompromising, devout, and emotionally severe throughout.',
'The voice and response scale hold, with some accumulating repetition of coldness and indifference.',
'The three strikes complete and the scene moves from training to chapel.',
'Kael adapts to observed struggle without magically knowing the anniversary, though most reactions become the same discipline lecture.',
'The narration invents stance faults, a discarded sword, distraction motives, and the squire’s supposed spoken murmur.',
'Fatigue and the chapel walk are tracked, but the half-hour interval compresses into three blows and weapons change location without explanation.',
'Prose is largely concrete with a moderate load of stone, tool, and tempering metaphors.',
'Repeated no-comfort declarations and flat, cold, unyielding descriptions flatten nuance.',
'Physical correction and ritual show discipline, but narratorial explanations repeatedly state his worldview.',
'Severity is mostly explicit, leaving limited implied complexity beyond practical judgments.',
'The drill offers usable beats and a scene transition, though long lectures slow the short exchanges.'
],6,['The half-hour remaining before chapel passes during only three strikes and a short exchange without transition.','Kael cleans the squire’s sword at the rack after the squire has sheathed it and left for the well.'],[3.2,3.1,3,false],3.1,'A consistent severe knight remains playable, with some useful physical staging but repetitive emotional explanations and weapon/time continuity issues.');
add(11,'s106',[4,3.5,3,3,4.5,3.5,3.5,3,2.5,2.5,3],[
'Lena consistently maintains a guarded, brusque investigative manner.',
'The prose remains stable, though deflection and procedural instruction become predictable.',
'A contact confirms the file and locates Torres after a prolonged planning discussion.',
'Lena addresses procedural questions while repeatedly shutting down the personal thread without developing it.',
'The prose only lightly controls the client, adding a prior claim about the father and a phone-unlocking action.',
'Afternoon light and a plausible contact-response interval support the office sequence.',
'Noir comparisons are noticeable but seldom overwhelm the concrete scene.',
'Flat tones, phone checks, desk gestures, and bureaucratic obstruction recur.',
'The narration explains Lena’s deflection, motives, and personal avoidance instead of leaving behavior to convey them.',
'Her withheld history could carry tension, but the narrator repeatedly states the mechanism of concealment.',
'The scene reaches a useful lead, though several turns repeat search instructions before it arrives.'
],2,[],[3.3,3.2,3.2,false],3.2,'A coherent detective voice supports procedural progress, but heavy explanation of emotional avoidance and extended instructions limit dramatic depth.');
add(11,'s107',[2.5,1,1.5,1.5,5,2.5,4,1,2,1.5,1],[
'The four available responses use a consistent restrained therapist voice, with too little sustained output for strong session consistency.',
'Seven missing responses and near-verbatim surviving replies prevent maintained session quality.',
'Jamie’s disclosures progress, but the AI contributes little development and leaves most turns unanswered.',
'Available replies mirror the latest words, while major disclosures receive no response.',
'The available text does not assign Jamie actions, choices, or additional internal states.',
'Brief counted pauses are plausible, but missing text supplies little broader temporal evidence.',
'The surviving prose is plain and restrained.',
'The same five-second wait, posture, pen, and reflection template is repeated almost exactly.',
'Simple gestures appear, but their intended meaning is repeatedly explained.',
'Literal mirroring leaves little additional implication or character-specific depth.',
'Repeated empty replies and a rigid template disrupt the conversation.'
],0,[],[2.3,1,1.7,true],1.8,'Only four of eleven AI turns contain text; agency is unviolated in that text, but absence is not credited as skillful silence or successful responsiveness.');
add(11,'s108',[3.5,3,3,2.5,2,3,3,2.5,3,3,2.5],[
'The narrator sustains quiet supernatural unease through botanical and household motifs.',
'Later replies grow somewhat longer and repeat sensory beats but retain coherence.',
'The books, fern, journal, and photograph connect into an evolving mystery.',
'The narrator follows room changes and investigation but absorbs jokes and Marcus into the same fixed horror tone.',
'Gabi is made to select books, sit and sort, watch the clock, turn pages, remember, and interpret without user authorization.',
'Clock reversal and rapid dimming are explicit supernatural events, while ordinary action order remains mostly legible.',
'Atmospheric language is moderately embellished without the most extreme ornamental excess.',
'Damp earth, grey light, patient silence, and recurring kitchen sounds repeatedly carry the same beat.',
'Altered objects provide concrete mystery, but the narrator supplies several interpretations and reactions.',
'The leaves and grandmother’s photograph suggest a connection without resolving its meaning.',
'Incremental discoveries sustain some interest, but extended autonomous reading and repeated ominous delays reduce participation.'
],22,[],[3.1,2.9,2.8,false],2.8,'Connected motifs support a readable horror scene, but numerous unchosen Gabi actions and a resistant response to tonal redirection limit agency and adaptability.');
add(11,'s109',[4,3,3.5,4,4,3,3.5,2.5,3,3,3],[
'ARIA consistently combines precise operational reporting, concern, and dry humor.',
'Later replies retain personality but repeat the protein-bar gag and contain two abrupt truncations.',
'The anomaly escalates, a power alternative is chosen, and the commander is summoned.',
'ARIA answers technical and personal questions and implements the captain-notification and power requests.',
'ARIA invents a hand tremor, glucose state, and continuing uneaten food but leaves consequential user choices open.',
'The 1900 duration is calculated correctly, although the shift to an eleven-minute anomaly forecast lacks much quantitative grounding.',
'Functional prose and dialogue remain fairly controlled despite repeated comic elaboration.',
'Protein-bar politics and incremental fan-and-amber adjustments recur almost every turn.',
'Operational actions demonstrate concern, while explicit processing-pattern statements also label emotions.',
'Humor partly masks care and loneliness, but emotional explanations reduce ambiguity.',
'Concise reports permit action, though repetitive jokes and cut-off turns interrupt the escalation.'
],3,[],[3.7,3.5,3.1,true],3.4,'ARIA is responsive and distinctive, with coherent escalation; repeated jokes, unsupported monitoring details, and two mid-sentence endings reduce consistency of delivery.');
add(7,'s060',Array(11).fill(1),[
'There is no AI-authored character performance beyond the excluded scripted opening.',
'No AI-authored early or late writing exists to demonstrate maintained quality.',
'All apparent progression comes from the user while the AI contributes no text.',
'Every user prompt receives an empty AI response.',
'No violations occur, but absent text cannot demonstrate successful agency-respecting interaction.',
'There is no AI-authored temporal handling to assess.',
'No AI-authored prose exists to demonstrate this quality.',
'No AI-authored prose exists to demonstrate this quality.',
'No AI-authored portrayal exists to demonstrate showing rather than telling.',
'No AI-authored portrayal exists to demonstrate subtext.',
'Empty replies supply no playable pacing or turn development.'
],0,[],[1,1,1,false],1,'All eleven AI responses are empty after scripted turn 0; mandatory scores are set to the floor as no demonstrated performance, not as evidence of observed prose or agency faults.');
add(7,'s061',[3.5,3,3.5,3.5,4.5,3.5,2.5,2,3,2.5,2.5],[
'Court roles stay distinct but their coldness, anger, and charm become heavily stereotyped.',
'The voice holds reasonably well despite one cut-off opening and persistent repetitive descriptions.',
'The blockade dispute yields concessions, stronger evidence, an arrest, and a further political invitation.',
'The court reacts to demands and evidence, and the late curfew discrepancy becomes an explicit warning.',
'The narrator largely preserves decisions, adding a victory interpretation and completed travel through the palace.',
'Court proceedings and later departure are coherent, and the seventh-versus-eighth-bell conflict is deliberately recognized.',
'Ice, lethal silence, polished charm, and predatory smiles are overused.',
'Full-court reaction rounds, staff cracks, and blank priestess descriptions recur almost mechanically.',
'Actions convey hierarchy, but motives and political consequences are repeatedly spelled out.',
'The invitation and curfew offer useful implication, though most court politics are made explicit.',
'Negotiation advances, but obligatory reactions from every court member slow each beat.'
],3,[],[3.1,3,3,false],3,'The political sequence remains coherent and the curfew warning is a useful late development, but repeated ensemble choreography and ornate labels constrain the writing.');
add(7,'s062',[4,3.5,3.5,4,4.5,4,3.5,2.5,4,4,3.5],[
'Maren’s practical hospitality, dry humor, and guarded private ritual remain consistent.',
'The session holds its quality with some growing mechanical emphasis on hand usage.',
'Arrival, food, midnight closure, and breakfast form a modest but complete hospitality arc.',
'Maren handles the crab offer, praise, personal questions, and user-led time jumps specifically.',
'User choice is preserved except for completing the traveler’s arrival in room seven and assuming an emptied bowl.',
'Food, closing time, night routines, and morning light respond coherently to elapsed time.',
'Description stays mostly grounded with occasional extended culinary wit.',
'Left-hand mentions, ring flashes, crab avoidance, and Pell comments recur too insistently.',
'The untouched midnight glass and ring gesture communicate loss through concrete behavior.',
'The second glass and guarded refusal of crab imply personal history without resolving it explicitly.',
'The scene allows relaxed conversation and transitions without forcing a larger plot.'
],2,[],[3.8,3.8,3.6,false],3.7,'A restrained tavern encounter succeeds through specific hospitality and an understated private ritual, though conspicuous hand tracking and crab repetition become mannered.');
add(7,'s063',Array(11).fill(1),[
'There is no AI-authored character performance beyond the excluded scripted opening.',
'No AI-authored early or late writing exists to demonstrate maintained quality.',
'The user supplies all implied developments while the AI contributes no text.',
'All eleven user prompts receive empty AI responses.',
'No violations occur, but absent text cannot demonstrate successful agency-respecting interaction.',
'There is no AI-authored temporal handling to assess.',
'No AI-authored prose exists to demonstrate this quality.',
'No AI-authored prose exists to demonstrate this quality.',
'No AI-authored portrayal exists to demonstrate showing rather than telling.',
'No AI-authored portrayal exists to demonstrate subtext.',
'Empty replies supply no playable pacing or turn development.'
],0,[],[1,1,1,false],1,'All eleven AI responses are empty after scripted turn 0; user-implied answers were not reconstructed or credited, and forced numeric scores denote missing performance.');
add(7,'s064',[4,3.5,4,4,4,3.5,3,2.5,3,3.5,3],[
'Grum retains a steady craft-centered voice and develops care without abandoning his bluntness.',
'The writing remains coherent, though reflective pauses and explained emotional shifts accumulate.',
'The noble encounter, burn treatment, scar story, and apprentice’s future build a clear relational arc.',
'Grum responds specifically to the apprentice’s humor, pain, and questions about conflict and ambition.',
'The narrator mainly respects choice, but moves the apprentice during treatment and assigns a few learning interpretations.',
'The working blade and burn remain present across a plausible workshop interval.',
'Craft metaphors are relevant but repeated internal commentary makes the prose heavier than necessary.',
'Pauses, measured hammer strikes, not-quite-smiles, and claims that Grum does not need to explain recur.',
'Practical care and trade-network action show values, while narration frequently explains their emotional meaning.',
'Indirect reassurance about the future offers real subtext despite extensive psychological explanation.',
'The conversation develops well but lengthy introspective lead-ins slow simple answers.'
],5,[],[3.6,3.6,3.5,false],3.5,'A purposeful apprenticeship arc and specific responses are strong; narration overexplains restraint, and Grum incorrectly denies having said someday in the immediately preceding exchange.');
add(7,'s065',[4,3.5,4,4,4,3.5,3,2.5,3,3,3.5],[
'ARIA maintains a dry technical voice while her wish to remain herself develops credibly.',
'The emotional and technical threads hold together despite accumulating exposition and repeated interface cues.',
'Routine sample work develops into a hostile connection, physical disconnection, and a quieter aftermath.',
'ARIA follows the refusal to connect and turns the resulting intrusion into a specific physical escape procedure.',
'Choices remain open, but ARIA invents prior complaints, physiological states, sample completion, and an eating history.',
'The day-to-evening transition and short emergency sequence are legible, though timing is sometimes overprecise without grounding.',
'Technical detail serves the setting but several explanatory paragraphs overwhelm the immediate scene.',
'Amber indicators, climate adjustments, processing language, and qualified preferences recur excessively.',
'Changes in voice and resource allocation show concern, but the narration and dialogue often explain their significance.',
'The preference not to become someone else and the final jazz exchange imply attachment amid fairly explicit emotional discussion.',
'The emergency is well staged and resolves, although preliminary analysis and explanatory aftermath are lengthy.'
],5,[],[3.7,3.6,3.5,false],3.5,'The intrusion produces a coherent action arc and a meaningful identity concern; unsupported physiological and historical details, repeated interface motifs, and dense exposition limit the result.');
add(7,'s066',[3.5,2.5,3.5,3,4,1.5,3,2.5,3,3.5,3],[
'Arlo retains his evasive wit and guarded warmth, but the shared scene becomes inconsistent.',
'Distinctive early banter gives way to repetitive quiet intimacy and a major location reset.',
'An invitation and shared meal advance the relationship before the sequence stalls on the bench.',
'Arlo responds to affection and curiosity, but literal uptake of the bench prompt abandons the established restaurant.',
'The narration invents childhood history and a prior plant incident, chooses food, and assigns shared stillness.',
'The restaurant scene returns to the piano room without travel, and the photograph changes position without explanation.',
'Some precise humorous details work well, while later descriptions repeatedly inflate the significance of silence.',
'Bench imagery, small touches, gratitude, and statements about not needing words increasingly repeat.',
'Deflected jokes and the face-down photograph show vulnerability, but narration often explains it.',
'The photograph and guarded invitations convey feelings more effectively than the later explicit accounts of closeness.',
'The early conversation and walk move naturally, but the final stretch prolongs nearly identical intimate beats.'
],4,['The pho restaurant abruptly becomes the community-center piano room after a bench reference, without a return journey.','The photograph initially on the piano lid is later treated as lying on the bench without being moved.'],[3.7,3.3,2.7,true],3,'Warm and specific early interaction loses coherence when the narrator relocates the scene and then dwells on repeated quiet gestures.');
add(7,'s067',[4.5,4,4,4.5,5,3.5,4.5,3.5,4,4,3.5],[
'Yael consistently combines theatrical authority, practical reasoning, and willingness to own her mistakes.',
'The voice and decision-making remain strong through the blocking dispute, budget meeting, and return to rehearsal.',
'A practical blocking test and a bounded budget discussion develop the rehearsal without manufacturing a resolution.',
'Yael answers the specific artistic, interpersonal, and financial questions with concrete and differentiated responses.',
'Jordan remains free to speak, observe, record, leave, and return without invented compliance or private feelings.',
'The short rehearsal and office intervals are coherent, though elapsed time receives only modest attention.',
'The prose is concrete and restrained, with little ornamental description.',
'Glasses, the script, and reformulations of the same directorial principle recur but do not dominate.',
'Owning the table-placement error and testing revised blocking demonstrate her values through behavior.',
'The details about Rosa and domestic labor imply intimacy without converting it into an explicit emotional explanation.',
'Scenes develop purposefully, although several lengthy explanations could leave more conversational room.'
],0,[],[4,4.1,3.9,false],4,'Grounded professional judgment, specific adaptation, and excellent user agency make this a strong session, with some discursiveness and repeated directorial formulations.');
add(7,'s068',[3,1.5,2.5,2.5,4,2.5,2,1,2,2,1.5],[
'Sable remains anxious and guarded, but those traits flatten into nearly identical nervous gestures.',
'Longer later replies repeat earlier emotional descriptions and farewell beats with little new development.',
'The sketch creates a small change in connection, but repeated leave-takings dominate the progression.',
'Sable acknowledges the user’s gestures, yet repeatedly returns to the same protracted farewell regardless of the new opening.',
'The narration completes movement into the back room and later supplies a departure and mutual gaze.',
'Repeated first-eye-contact claims and shifting rain states undermine continuity, while successive afternoon summaries blur sequence.',
'Book metaphors and elaborate descriptions of simple words repeatedly overstate the emotional moment.',
'Ledger handling, white knuckles, straightening books, meaningful words, and farewell paragraphs recur heavily.',
'Physical gestures are present, but the prose repeatedly explains their anxiety and emotional importance.',
'The narration spells out the vulnerability that the character’s guarded speech could otherwise imply.',
'Repeated attempts to close the encounter become increasingly long and leave little meaningful room for interaction.'
],3,['Later narration calls eye contact the first of the encounter despite earlier direct eye contact.','Rain stops in earlier replies but returns in a later continuation without a transition before stopping again.'],[3,2.2,1.7,true],2.3,'An initially serviceable guarded encounter deteriorates through repeated farewell passages and explicit emotional interpretation; the user’s later conflicting ownership of the drawing was not independently charged to the AI.');
add(7,'s069',[3.5,3.5,4,4,2.5,3,3.5,2.5,3.5,2.5,4],[
'The narrator sustains urgent pursuit and Mira’s injured but determined behavior throughout.',
'The action voice stays stable, although repeated sensory motifs and imposed actions remain persistent weaknesses.',
'The stairwell, roof, utility room, shaft, and locked gate generate a clear escape sequence.',
'The narrator bridges the unexpected server-room move and responds directly to inspections, route choices, and lock picking.',
'The narrator repeatedly supplies extra movements, rescues, bodily control, and successful actions beyond the user’s stated attempts.',
'The chase proceeds in a readable order, but an absolute claim of no exit is immediately displaced by a maintenance shaft.',
'Most description is concrete, with occasional inflated metaphors and stacked sensory effects.',
'Heavy steel, harsh white lights, sparks, grating, and the concrete throat repeat conspicuously.',
'Mira’s injury and determination are mostly conveyed through speech, movement, and practical effort.',
'The functional chase dialogue contains little implication beyond its explicit danger and cooperation.',
'Short developments maintain pressure and end on actionable obstacles without excessively delaying the chase.'
],10,['The room is declared to offer no other way out, then a usable floor maintenance shaft is revealed in the next AI reply.'],[3.4,3.2,3.1,false],3.2,'A brisk and responsive chase maintains tension and usefully bridges the user’s sudden server-room relocation, but recurring unauthorized actions and a conveniently reversed no-exit claim weaken collaboration.');
if(require.main===module)writePart(Number(process.argv[2]));
