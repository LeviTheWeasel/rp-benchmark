from pathlib import Path
from reportlab.pdfgen import canvas
p=Path(__file__).parent
c=canvas.Canvas(str(p/'Hemmingway-1_PlotPoints_Final.pdf'),pagesize=(1080,1560))
c.setTitle('Hemmingway-1 | PlotPoints')
c.drawImage(str(p/'Hemmingway-1_PlotPoints.png'),0,0,width=1080,height=1560)
c.showPage()
c.save()
