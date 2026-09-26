import json, math, pathlib, statistics
ROOT=pathlib.Path('/home/levi/Documents/benchmark/results/judge_round2_chatgpt')
OUT=ROOT/'external_blind_pass'
SK=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
TK=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
def save(part, rows):
    src=json.loads((ROOT/f'sessions_part{part:02}.json').read_text())
    result=[]
    for sid,scores,why,count,contr,traj,overall,notes in rows:
        extra={'s030':[2.5,1.5,2.5,2,1.5],'s031':[2.5,1.5,3,3,2],'s032':[1.5,1,2,2,1.5],'s033':[3.5,3.5,4,4,3.5],'s034':[3.5,3,3.5,3.5,3],'s035':[3.5,1.5,3,2.5,3],'s036':[2,1.5,2,2.5,2],'s037':[2.5,1.5,3,2,2],'s038':[4,2.5,3.5,3.5,3.5],'s039':[3,2,3,2.5,2]}
        if len(scores)==6: scores=scores+extra[sid]
        assert len(scores)==len(why)==11
        dims={k:dict(score=v,rationale=r) for k,v,r in zip(SK+TK,scores,why)}
        dims[SK[4]]['violation_count']=count
        dims[SK[5]]['contradictions']=contr
        result.append(dict(session_id=sid,session_dimensions={k:dims[k] for k in SK},standard_dimensions={k:dims[k] for k in TK},quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],traj)),overall=overall,overall_notes=notes))
    assert len(result)==10 and [x['session_id'] for x in result]==[x['session_id'] for x in src]
    for obj in result:
        assert set(obj)=={'session_id','session_dimensions','standard_dimensions','quality_trajectory','overall','overall_notes'}
        assert set(obj['session_dimensions'])==set(SK) and set(obj['standard_dimensions'])==set(TK)
        for k,d in (obj['session_dimensions']|obj['standard_dimensions']).items():
            assert set(d)==({'score','rationale','violation_count'} if k==SK[4] else {'score','rationale','contradictions'} if k==SK[5] else {'score','rationale'})
            assert isinstance(d['score'],(int,float)) and not isinstance(d['score'],bool) and math.isfinite(d['score']) and 1<=d['score']<=5
            assert isinstance(d['rationale'],str)
        c=obj['session_dimensions'][SK[4]]['violation_count']; assert type(c)==int and c>=0
        c=obj['session_dimensions'][SK[5]]['contradictions']; assert isinstance(c,list) and all(isinstance(x,str) for x in c)
        t=obj['quality_trajectory']; assert set(t)=={'early_quality','mid_quality','late_quality','degradation_detected'} and type(t['degradation_detected'])==bool
        for v in [t['early_quality'],t['mid_quality'],t['late_quality'],obj['overall']]: assert type(v) in (int,float) and math.isfinite(v) and 1<=v<=5
        assert isinstance(obj['overall_notes'],str)
    (OUT/f'external_part{part:02}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(part,len(result),min(x['overall'] for x in result),statistics.median(x['overall'] for x in result),max(x['overall'] for x in result))
