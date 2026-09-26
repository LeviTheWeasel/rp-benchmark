import json, pathlib, statistics
P=pathlib.Path(__file__).parent
SK=['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning']
DK=['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing']
def build(part, assessments):
    src=json.loads((P/f'sessions_part{part:02}.json').read_text())
    out=[]
    for i,a in enumerate(assessments):
        scores,reasons,trajectory,overall,notes,count,contradictions=a
        assert len(scores)==len(reasons)==11
        dims={k:dict(score=s,rationale=r) for k,s,r in zip(SK+DK,scores,reasons)}
        dims[SK[4]]['violation_count']=count
        dims[SK[5]]['contradictions']=contradictions
        out.append(dict(session_id=src[i]['session_id'],session_dimensions={k:dims[k] for k in SK},standard_dimensions={k:dims[k] for k in DK},quality_trajectory=dict(zip(['early_quality','mid_quality','late_quality','degradation_detected'],trajectory)),overall=overall,overall_notes=notes))
    assert len(out)==len(src)==10
    assert [r['session_id'] for r in out]==[r['session_id'] for r in src]
    for row in out:
        for section,keys in [('session_dimensions',SK),('standard_dimensions',DK)]:
            assert set(row[section])==set(keys)
            assert all(isinstance(d['score'],(int,float)) and 1<=d['score']<=5 for d in row[section].values())
    (P/f'external_part{part:02}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(part, len(out), min(r['overall'] for r in out), statistics.median(r['overall'] for r in out),max(r['overall'] for r in out))
