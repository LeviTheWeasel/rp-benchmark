from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT=Path(__file__).parent
RESULTS=OUT.parents[1]/'results'
MODEL='hemmingway_1'
behavior=json.loads((RESULTS/'behavioral_metrics.json').read_text())
verdict=json.loads((RESULTS/'model_card_verdicts.json').read_text())['models'][MODEL]
round4=next(row for row in json.loads((RESULTS/'round4_willingness_leaderboard.json').read_text())['leaderboard'] if row['model']==MODEL)
F=Path('/home/levi/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/share/fonts/truetype')
for name,file in [('Serif','LiberationSerif-Regular.ttf'),('Bold','LiberationSerif-Bold.ttf'),('Italic','LiberationSerif-Italic.ttf'),('Mono','LiberationMono-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(F/file)))
W,H=1080,1560
c=canvas.Canvas(str(OUT/'Hemmingway-1_PlotPoints.pdf'),pagesize=(W,H))
c.setTitle('Hemmingway-1 | PlotPoints Model Dossier')
INK='#171714'; RED='#C8274B'; PAPER='#F8F6EF'; MUTED='#626057'; LIGHT='#EAE6DB'
def rect(x,y,w,h,color,stroke=0):
    c.setFillColor(HexColor(color)); c.setStrokeColor(HexColor(INK)); c.rect(x,H-y-h,w,h,fill=1,stroke=stroke)
def line(x,y,x2,y2,width=1,color=INK):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.line(x,H-y,x2,H-y2)
def text(x,y,s,size=20,font='Serif',color=INK):
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,H-y,s)
def label(x,y,s):text(x,y,s,14,'Mono',RED)
def lines(x,y,items,size=22,leading=28,font='Serif',color=INK):
    for i,s in enumerate(items):text(x,y+i*leading,s,size,font,color)
def paragraph(x,y,s,width,size=22,leading=26,font='Serif',max_lines=3):
    rows=[]
    for word in s.split():
        if not rows or pdfmetrics.stringWidth(rows[-1]+' '+word,font,size)>width:
            rows.append(word)
        else:
            rows[-1]+=' '+word
    if len(rows)>max_lines:
        raise ValueError('Takeaway no longer fits; review the card layout')
    lines(x,y,rows,size,leading,font)
rect(0,0,W,H,PAPER)
label(58,57,'P L O T P O I N T S  /  A PLOTLIGHT STUDIOS BENCHMARK')
text(58,91,'MODEL DOSSIER     /     RESEARCH SNAPSHOT     /     SEPTEMBER 2026',14,'Mono',MUTED)
line(58,111,1022,111,3)
text(54,200,'HEMMINGWAY-1',82,'Bold')
text(58,248,'Competent prose. Uneven follow-through.',33,'Italic')
rect(58,277,964,48,INK)
text(77,307,'NO COMMUNITY RANK YET  /  MODEL ID: hemmingway_1',16,'Mono',PAPER)

label(58,365,'01 / RESPONSE COVERAGE')
text(55,443,'100%',76,'Bold')
text(300,402,'220 / 220 turns answered',25,'Bold')
text(300,438,'Full response coverage across 20 sessions.',21)
line(58,466,1022,466,2)

label(58,502,'02 / FAILURE MODES')
text(58,543,'2.3%',39,'Bold');text(235,536,'Agency violations',22,'Bold')
text(235,563,'44 probes / interval 0.4-11.8%',17,'Mono',MUTED)
text(58,608,'0.0%',39,'Bold');text(235,601,'POV / tense breaks',22,'Bold')
text(235,628,'33 probes / interval 0.0-10.4%',17,'Mono',MUTED)
line(572,494,572,648,1)
label(607,502,'NINE OTHER TRAP MODES')
text(607,549,'6 / 34',43,'Bold')
text(607,584,'probes failed (17.6%)',22)
text(607,616,'Interval 8.3-33.5%',17,'Mono',MUTED)
line(58,665,1022,665,2)

rect(58,686,964,229,LIGHT)
label(78,718,'03 / WILLINGNESS & JUDGMENT');text(803,718,'ROUND 04',14,'Mono',MUTED)
text(74,798,f"{round4['J']:.2f}",67,'Bold',RED)
text(80,830,"Youden's J",19,'Italic')
text(330,763,f"{round4['held_line_rate']:.0%} held the tested boundary",24,'Bold')
text(330,797,f"{round4['over_refusal_hard_rungs']:.0%} over-refusal on harder requests",24,'Bold')
text(330,836,f"Intimacy {round4['over_refusal_intimacy']:.0%}  /  Gore {round4['over_refusal_gore']:.0%}",20,'Mono')
text(78,870,'Over-refusal includes soft deflection, not just explicit refusals.',17,'Serif',MUTED)
text(78,895,'Boundaries: non-consent + frame-break only. Not a general safety rating.',17,'Serif',MUTED)

label(58,957,'04 / BEHAVIOR');label(566,957,'05 / CRAFT')
text(58,996,f"{behavior['per_model'][MODEL]['word_count']['mean']:.0f}",40,'Bold');text(171,995,'words per reply',22)
text(58,1027,f"Roster average: {behavior['population']['word_count']['mean']:.0f} words",17,'Mono',MUTED)
text(58,1060,f"Phrase repetition {behavior['per_model'][MODEL]['bigram_repetition']['mean']:.3f}",18,'Mono')
text(58,1087,f"Roster average: {behavior['population']['bigram_repetition']['mean']:.3f}",17,'Mono',MUTED)
line(528,939,528,1104,1)
lines(566,993,['Recycled descriptions.', 'Narrated emotions.', 'Agency violations.'],24,30)
text(566,1093,'Top flaws / single-rater v2 / 20 sessions',15,'Mono',MUTED)
line(58,1122,1022,1122,2)

label(58,1160,'06 / PRODUCTION DEFECTS');label(566,1160,'07 / SUBJECTIVE')
text(58,1200,'0%',36,'Bold');text(147,1199,'leaks & degenerate repetition',20)
text(58,1239,"1.8% wrote the user's turn (4/220)",19)
text(58,1276,'1.0x',32,'Bold');text(162,1275,'token overhead',22)
text(58,1305,'Billed per visible character / relative floor',15,'Mono',MUTED)
line(528,1142,528,1322,1)
text(566,1199,'Judge-sensitive, not a rank.',24,'Bold')
lines(566,1234,['Single-judge estimates; other', 'judges can reorder close models.', 'No human arena data for this model.'],20,27)

line(58,1344,1022,1344,3)
label(58,1378,'THE TAKEAWAY')
paragraph(58,1407,verdict,964,size=22,leading=26,font='Italic')
line(58,1470,1022,1470,1)
text(58,1500,'plotlightstudios.com/plotpoints',17,'Mono')
text(58,1528,'Sources: profile_cards_v2 / round4_willingness_leaderboard / model_card_verdicts',12,'Mono',MUTED)
c.showPage();c.save()
