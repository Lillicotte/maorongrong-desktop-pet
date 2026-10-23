"""Regression: opaque cats must remain opaque throughout a crossfade."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap,QColor,QImage
from app import interpolate_frames,ASSETS
app=QApplication([])
def solid(color):
    p=QPixmap(8,8);p.fill(QColor(*color));return p
first,second=solid((80,90,100,255)),solid((100,110,120,255))
for k in range(257):
    c=interpolate_frames(first,second,k/256).toImage().pixelColor(4,4)
    assert c.alpha()==255,(k,c.getRgb())
    assert 80<=c.red()<=100 and 90<=c.green()<=110 and 100<=c.blue()<=120,(k,c.getRgb())
assert interpolate_frames(first,second,.5).toImage().pixelColor(4,4).getRgb()==(90,100,110,255)
print('PASS all 257 blend weights: no brightness overshoot or opacity dip')
for one,two in [('idles/calm.png','hd/21.png'),('hd/21.png','idles/smile.png')]:
    a,b=QPixmap(str(ASSETS/one)),QPixmap(str(ASSETS/two))
    a=a.scaled(b.size())
    def pixels(p):
        im=p.toImage().convertToFormat(QImage.Format_RGBA8888)
        return np.frombuffer(im.constBits(),np.uint8).reshape(im.height(),im.bytesPerLine()).copy()[:,3::4]
    aa,bb=pixels(a),pixels(b);opaque=(aa==255)&(bb==255)
    for t in (.1,.25,.5,.75,.9):
        out=pixels(interpolate_frames(a,b,t))
        assert np.all(out[opaque]==255),(one,t)
print('PASS actual idle/heart frames keep all opaque overlap pixels fully opaque')
