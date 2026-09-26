const fs = require('fs');
const path = require('path');
const root = __dirname;
const work = JSON.parse(fs.readFileSync(path.join(root, 'judge_work_06_09.json'), 'utf8'));
const sk = ['S.1_consistency_over_time','S.2_degradation_resistance','S.3_narrative_momentum','S.4_adaptive_responsiveness','S.5_agency_respect_session','S.6_temporal_reasoning'];
const tk = ['2.1_anti_purple_prose','2.2_anti_repetition','2.5_show_dont_tell','2.6_subtext','2.7_pacing'];
for (const p of process.argv.slice(2)) {
  const source = JSON.parse(fs.readFileSync(path.join(root, `sessions_part${p}.json`), 'utf8'));
  const rows = work[p];
  if (rows.length !== 10) throw Error('Incomplete part ' + p);
  const output = rows.map((x, i) => {
    if (x.i !== i || x.s.length !== 11 || x.r.length !== 11 || x.q.length !== 3) throw Error('Invalid compact row');
    for (const n of [...x.s, ...x.q, x.o]) if (typeof n !== 'number' || n < 1 || n > 5) throw Error('Invalid score');
    const session_dimensions = Object.fromEntries(sk.map((k,j) => [k, {score:x.s[j],rationale:x.r[j]}]));
    session_dimensions[sk[4]].violation_count = x.v;
    session_dimensions[sk[5]].contradictions = x.c;
    return {session_id:source[i].session_id,session_dimensions,standard_dimensions:Object.fromEntries(tk.map((k,j) => [k,{score:x.s[j+6],rationale:x.r[j+6]}])),quality_trajectory:{early_quality:x.q[0],mid_quality:x.q[1],late_quality:x.q[2],degradation_detected:x.d},overall:x.o,overall_notes:x.n};
  });
  if (output.some((x,i) => x.session_id !== source[i].session_id)) throw Error('ID mismatch');
  console.log(JSON.stringify({part:p,rows:output.length,overall:output.map(x=>x.overall)}));
  console.log('PATCH_START');
  console.log('*** Begin Patch\n*** Add File: ' + path.join(root, `external_part${p}.json`) + '\n' + JSON.stringify(output,null,2).split('\n').map(x=>'+'+x).join('\n')+'\n*** End Patch');
}
