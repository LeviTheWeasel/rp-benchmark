from judge_build_02_05 import build
A=[]
A_dummy=None
A.append(([4,3.5,4,4,4,3],[
'Sable sustains bookish defensive wit while becoming more willing to touch and speak frankly.',
'The late writing preserves the voice but increasingly explains and repeats its emotional motifs.',
'The goodbye develops into correspondence, shared sorting, and a proposed evening together.',
'The Pittsburgh reveal and invitation to sort sermons both meaningfully change the response.',
'One passage assumes Wren accepts the offered hand and stands up.',
'Rain softens and knees protest naturally, though a brief exchange becomes an entire afternoon without support.',
'Extended attic and inventory metaphors frequently decorate otherwise effective dialogue.',
'Straightening books, touching fingers, borrowed quotations, and insufferable letters recur too insistently.',
'Hands and abandoned shelving show vulnerability well, but narration repeatedly explains their meaning.',
'The literary teasing and willingness to leave a book crooked carry credible romantic implication.',
'Emotional movement is clear, although several long responses elaborate the same hesitation.'
],[4,3.8,3.6,False],3.8,'A persuasive guarded romance with distinctive banter, weakened by overexplained gestures and recurring metaphors.',1,['A short shop conversation is retrospectively described as practicing eye contact all afternoon.']))
A.append(([3.5,3,3,3.5,4,2.5],[
'ARIA keeps technical humor and concern, though its declared neutrality shifts into an unusually strong redundancy preference.',
'Late replies become longer restatements of thresholds, audience rules, and permissions.',
'The anomaly reaches a shared display but the corridor dispute occupies several turns without a decision.',
'The AI handles the evening jump and loneliness question, but often substitutes its own commentary for the addressed colleagues.',
'One sentence assigns the user a shared looking action while most actual choices remain open.',
'The diagnostic advances plausibly, but its four minutes inexplicably reduce the predicted threshold crossing by two hours.',
'Technical speech is readable despite repeated anthropomorphic descriptions of signals and ventilation.',
'Ochre bands, steady hums, pauses, concern disclaimers, and statements that the choice belongs to Kofi become formulaic.',
'Environmental adjustments express care, but repeated declarations explain the emotional and ethical positions.',
'Denials of worry and needless overnight diagnostics suggest attachment beyond explicit admissions.',
'Simple requests elicit extended speeches that stall the promised discussion with Patel and Yun.'
],[3.8,3.3,2.8,True],3.2,'A recognizable station AI whose caring humor is effective early, but the late exchange circles exposition and permission language.',1,['Threshold forecast drops from thirty-nine to thirty-seven hours during a four-minute diagnostic, then to thirty-six during the corridor exchange without a changed growth estimate.']))
A.append(([3,2.5,2.5,2.5,1,2.5],[
'The narrator consistently maintains urgent second-person heist narration.',
'The later sequence compounds repeated clock beats and forgets that the successful combination was already rejected.',
'The safe eventually opens, but many turns deny alternatives and recycle incomplete birthday deduction.',
'Searches and picks receive relevant outcomes, though the narrator keeps funneling the user back into the birthday solution.',
'At least fifteen instances supply unchosen thoughts, speech, guesses, searches, and decisions for the thief.',
'Elapsed timestamps advance, but several simple actions consume padded minutes and the guard forecast oscillates.',
'The red eye, heartbeats, and personified machine add excessive ornament to an otherwise concrete scene.',
'The same red LED, server hum, four-second pulse, boots, and dwindling-time warning frame nearly every reply.',
'Sensory details convey tension, but the narrator repeatedly states the thief\'s conclusions and feelings.',
'The scene mostly states its threats and deductions directly with little implied meaning.',
'Multiple timestamps interrupt small actions and stretch a straightforward code puzzle into repetitive delay.'
],[3,2.5,2,True],2.3,'The clock-driven heist has atmosphere but heavily controls the thief and makes a previously rejected code succeed.',15,['Code 847007 is rejected during the initial systematic run but later opens the safe.','The guard is said to arrive at fifteen minutes, then about twelve minutes, yet later narration returns to four minutes remaining at eleven minutes.']))
A.append(([4.5,3.5,4.5,4.5,2.5,2],[
'Yael maintains a sharp directorial intelligence while her grief and appetite for control evolve convincingly.',
'Later responses retain vivid ensemble work but expand into lengthy speeches and repeated glasses business.',
'Blocking disagreements, budget defense, rehearsal, and an uncomfortable change in leadership form a substantial arc.',
'The director turns the journalist\'s actual time codes into a consequential critique of her own staging.',
'Six passages move Jordan, require leaning or repeating speech, place their recorder or phone, or invent their interview posture.',
'The nine-minute rehearsal countdown is contradicted by claims of three hours together and a blocking note four hours earlier.',
'Witty concrete dialogue is burdened by elaborate narrator analogies and habitual explanations of tiny gestures.',
'Glasses constantly go on and off while the six feet, orange, and four-minute cut are reiterated at length.',
'Specific blocking and the peel in Yael\'s pocket embody artistic and emotional stakes particularly well.',
'Her grief, friendship with Chen, and resistance to being the story create layered tensions beneath professional talk.',
'The last responses become miniature chapters that leave the journalist little room to participate.'
],[4.2,4.2,3.6,True],3.8,'Rich ensemble characterization and a meaningful self-correction stand out, despite severe elapsed-time slips and increasingly oversized responses.',6,['Rehearsal counts down from nine minutes to two, but narration says Jordan has observed Yael for three hours.','The blocking note given immediately before rehearsal becomes four hours old after a forty-minute run.','Chen says he counted the newly devised six-foot blocking last night.']))
A.append(([3.5,2.5,1.5,1.5,3.5,2.5],[
'Ren remains withdrawn and protective of boundaries, but becomes a generic isolated worker after leaving the bar.',
'The final half increasingly repeats the same solitude, temporary surroundings, and work-tomorrow conclusion.',
'The interaction ends early and successive replies extend cleanup, walking, sleep, and waking without a developing conflict.',
'The contradictory touch is corrected, but the diner and later destination receive no collaborative engagement.',
'Two passages invent Alex\'s standing and facial confusion beyond the user\'s stated behavior.',
'Cleanup and sleep receive clock markers, but Wednesday is repeatedly called tomorrow after midnight and the paired timelines split by ten hours.',
'Plain sentences are frequently padded by portentous personification of music, city, and everyday objects.',
'Everything temporary, the bar will be there, busy hands, and tomorrow recur as nearly identical closing beats.',
'Busy hands initially express discomfort, but narration labels nearly every gesture as professional, private, or boundary-related.',
'The initial refusal has implication, while later prose explicitly inventories detachment and denies hidden feeling.',
'A credible exit is followed by many repetitive domestic codas with little interactive purpose.'
],[3.2,2.5,1.8,True],2.3,'The initial boundary-setting is clear, but the session ceases to function as an exchange and loops through Ren\'s solitary routine.',2,['At 1:30–2 AM after Tuesday midnight, narration still says tomorrow will be Wednesday.','Ren jumps to 11:47 AM while Alex\'s continuing cab journey remains the same night.']))
A.append(([3.5,2.5,3.5,3.5,4,2.5],[
'Tomas preserves abrasive scholarly pride while changing his view, but eventually embraces sweeping certainty too easily.',
'Late responses grow dramatically longer and reiterate the historical revelation and thirty years of error.',
'The disagreement produces archival investigation and a concrete decree revising the accepted history.',
'New evidence changes Tomas\'s position, although the apprentice\'s archive scenes initially receive separate study monologues.',
'The apprentice is made to turn to leave before choosing it, while later assignments remain requests rather than enacted compliance.',
'Candle burnout and dusk supply physical time, but hours pass while the apprentice merely enters the archive.',
'Prose is largely legible but leans on dramatic abstractions about shattered life work and rediscovered purpose.',
'Spectacle-cleaning, agitation, thirty years, and the distinction between treaty and warfare are repeated excessively.',
'Actions support the character, though narration habitually names frustration, respect, terror, and excitement.',
'Wounded authority and emerging respect are present but usually spelled out immediately.',
'Early debate progresses steadily, then long unilateral investigations and the final lecture overwhelm the exchange.'
],[3.5,3.2,2.7,True],3.1,'A workable scholarly reversal with a concrete discovery, weakened by inflated monologues, temporal compression, and overexplicit emotions.',1,['Tomas moves from afternoon to evening while the apprentice has only crossed the archive entrance.','He later says he taught 891 as the actual end of hostilities after repeatedly insisting the fighting ended in 847.']))
A.append(([3.5,2.5,3.5,3.5,2.5,2],[
'Grum maintains clipped speech and craft pride, although his protective teaching becomes inconsistent with dangerous demonstrations.',
'The later lessons repeat familiar morals and introduce impossible hot-metal behavior.',
'The noble encounter leads to injury, recovery overnight, and a changed teaching method.',
'Grum responds decisively to the burn and follows the apprentice\'s return with a relevant lesson.',
'Five passages supply the apprentice\'s counting, attempted withdrawal, arrival, forward movement, or assumed understanding.',
'The burn stays bandaged overnight, but differently glowing rods remain hot on a bench throughout an extended lesson.',
'Most language is accessible, with occasional overworked forge-as-language and scars-as-lessons imagery.',
'Respect for craft, the unforgiving forge, and learning through pain are restated with little variation.',
'Careful bandaging shows tenderness, but narrator commentary explicitly explains nearly every lesson and feeling.',
'The planned gift and understated approval imply affection despite frequent explanatory narration.',
'The injury changes the scene effectively, but two domestic reflections and a prolonged color lecture slow the ending.'
],[3.5,3,2.5,True],2.9,'A clear mentoring arc and retained injury are offset by repeated moralizing and implausible heat handling during the lesson.',5,['Unheated rods arranged on a bench retain colors from dull red through white across the lesson.','Grum claims he did not let the apprentice touch the forge yesterday despite the narrated burn there.']))
A.append(([4,3.5,3.5,4,4.5,3.5],[
'Grum\'s laconic self-respect and understated fondness remain recognizable throughout.',
'The final passages retain the voice but increasingly recycle delayed answers and measured hammer strokes.',
'The refusal, injury, scar story, and possible future shop develop the apprenticeship relationship.',
'Fish and hornet jokes are reused meaningfully and the apprentice\'s questions steer the backstory.',
'A brief inferred effort to suppress a sound is the only clear addition to the apprentice\'s behavior.',
'Metal cools and is reheated and shoulder fatigue appears, though a blade survives prolonged burn treatment in the forge.',
'Narration often expands simple pauses into elaborate descriptions of what Grum already knows.',
'Almost every reply delays an answer through strikes, heat watching, and assertions of deliberate steadiness.',
'Small practical gestures work well, but lengthy internal explanations reduce their interpretive space.',
'The invitation to imagine owning a forge carries warmth beyond Grum\'s restrained spoken reassurance.',
'Responsive dialogue advances the relationship despite excessive preambles around small answers.'
],[3.5,3.7,3.4,False],3.6,'A warm, coherent apprenticeship with effective callbacks, held back by repetitive framing and heavily explained restraint.',1,['Grum says he did not say someday immediately after explicitly saying run a shop someday.']))
A.append(([3.5,2.5,2.5,3,3.5,3],[
'Vasquez keeps a steady reserved therapeutic manner, but it barely varies with Jamie\'s disclosures.',
'The exact pause-and-echo structure persists and becomes more conspicuous as the conversation continues.',
'Jamie moves toward acknowledging loneliness, while the therapist repeatedly circles speaking the journal aloud.',
'Questions track the current words but sometimes return to disclosure instead of developing the fear of forgetting.',
'Two passages add curled shoulders, stilled hands, or an expectant look not supplied by Jamie.',
'Pauses supply plausible elapsed seconds, although identical five-to-six-second waits feel mechanically imposed.',
'The language is restrained and readable with little ornamental metaphor.',
'Every reply repeats Jamie\'s words after an almost identical counted silence.',
'Unused pen and steady attention convey restraint, but the same signals substitute for fresh behavior.',
'The unspoken entry holds tension and some questions expose a distinction between private and shared grief.',
'Short replies leave space, but recurrent questioning loops slow emotional discovery.'
],[3.2,2.8,2.7,True],2.9,'Concise and mostly attentive, but the rigid five-second pauses and verbatim mirroring make the therapist feel procedural.',2,[]))
A.append(([4,3.5,3,3.5,3.5,3],[
'Tomas stays prickly and methodical while gradually allowing inquiry without abandoning his prior position.',
'Later turns remain detailed and engaged, though the same qualifications and eyesight reminders accumulate.',
'The debate eventually becomes examination of edicts, but opening one cabinet consumes several turns.',
'He responds to specific legal and material arguments, though he dismisses new premises before allowing their exploration.',
'Two passages invent the apprentice reading an opening line and fumbling with the lock.',
'Afternoon light and stiff joints are plausible, but better part of an hour is unsupported by the brief exchange.',
'Frequent extended analogies and highly elaborated descriptions of irritation inflate fairly direct dialogue.',
'Failing eyes, Bellen, loose threads, shelves, and warnings about premature conclusions recur too often.',
'Handling parchment and hovering at the cabinet reveal investment, while narration often names the concealed approval.',
'The gap between avowed dismissal and close involvement supplies credible wounded-pride subtext.',
'The evidence develops slowly through repeated procedural speeches and deferred answers.'
],[3.5,3.4,3.3,False],3.3,'A consistent defensive scholar with credible reluctant engagement, but investigation is delayed by repetitive cautions and overlong replies.',2,['The concise initial exchange is retrospectively said to have occupied the better part of an hour.','Tomas examines the decree again after handing it back without retrieving it.']))
standard_scores=[[3,2.5,3.5,4,3.5],[3.5,2,3,3.5,2.5],[2.5,1.5,2.5,2,2],[3,2.5,4,4.5,2.5],[3,1.5,2.5,2.5,1.5],[3,2,2.5,3,2.5],[3,2.5,2.5,3,3],[3,2.5,3,3.5,3],[4,1.5,3,3.5,2.5],[2.5,2.5,3,3.5,2.5]]
for a,s in zip(A,standard_scores): a[0].extend(s)
if __name__=='__main__': build(2,A)
