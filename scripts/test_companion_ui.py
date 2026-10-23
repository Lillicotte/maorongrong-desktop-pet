"""Exercise rule-driven animation handoffs, actual mouse events, controls and movement."""
import os,sys,time,math
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QPushButton,QLabel
from PySide6.QtCore import Qt,QPoint,QSettings
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from app import Pet

class RNG:
 def __init__(self,choices=(),roll=.55):self.choices=list(choices);self.roll=roll
 def choice(self,pool):
  value=self.choices.pop(0) if self.choices else pool[0]
  assert value in pool,(value,pool)
  return value
 def random(self):return self.roll

app=QApplication([]);app.setQuitOnLastWindowClosed(False)
QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc');app.setFont(QFont('Microsoft YaHei UI',9))
s=QSettings('Maorongrong','JellyCat');saved={k:s.value(k) for k in s.allKeys()}
p=Pet();p.tick_timer.stop();p.audio_timer.stop();p.needs_timer.stop();p.audio_active=False
p.affection=40;p.hunger=75;p.energy=80;p.set_quiet(False);p.set_size(240);p.show();p.open_panel();QTest.qWait(250)
def settled(n,timeout=5):
 end=time.monotonic()+timeout
 while p.transitioning and time.monotonic()<end:QTest.qWait(25)
 assert p.current_id==n and p.rules.state==n and not p.transitioning,(n,p.current_id,p.rules.state,p.transitioning)
def click():
 QTest.mouseClick(p,Qt.LeftButton,Qt.NoModifier,QPoint(p.width()//2,round(p.height()*.64)))
 QTest.qWait(QApplication.doubleClickInterval()+40)
def expire():
 p.rules.deadline=time.monotonic()-.01;p.tick()
try:
 texts=[label.text() for label in p.panel.findChildren(QLabel)]
 assert '猫溶溶小屋' in texts and 'Memento Mori~~' in texts
 box=next(b for b in p.panel.findChildren(QPushButton) if b.text()=='情绪盒子')
 p.rules.rng=RNG([4]);settled(0);click()
 assert p.rules.state==4 and p.affection==42 and p.energy==79,(p.rules.state,p.affection,p.energy,p.click_timer.isActive(),p.movie.fileName())
 settled(4);p.pat();assert p.affection==52 and p.rules.state==25 and p.energy==78
 settled(25);expire();assert p.rules.state==3;settled(3)
 print('PASS real left click +2, pat +10, energy cost and 10% flower reaction',flush=True)
 p.move(200,200);p.next_walk=0;p.roaming=True;before=(p.affection,p.hunger,p.energy)
 for _ in range(10):p.tick()
 assert p.moving and math.isclose(math.hypot(*p.velocity),.8)
 assert (p.affection,p.hunger,p.energy)==before
 p.next_walk=0;p.walk_until=0;p.tick();assert p.moving
 expire();assert p.rules.state==0;settled(0)
 print('PASS flower continuously roams at double speed, freezes losses and returns normally',flush=True)
 p.select_expression(7);settled(7);before=(p.affection,p.hunger,p.energy);position=p.pos()
 click();p.pat();p.feed();p.emotion_box();p.home();p.select_expression(4)
 assert p.rules.state==7 and p.pos()==position and (p.affection,p.hunger,p.energy)==before and p.drag_start is None
 p.panel.tabs.setCurrentIndex(1);assert p.current_id==13 and p.rules.state==7
 expire();assert p.rules.state==9 and p.current_id==13
 p.panel.tabs.setCurrentIndex(0);settled(9);click();settled(0)
 print('PASS anger blocks left clicks/drag/home/buttons; settings preserves timer; fire click returns normally',flush=True)
 p.rules.rng=RNG([14]);box.click();assert p.rules.state==14;settled(14)
 expire();assert p.rules.state==16;settled(16);click();assert p.rules.state==18;settled(18);expire();settled(0)
 p.rules.rng=RNG([19]);box.click();settled(19);expire();assert p.rules.state==10;settled(10)
 print('PASS emotion-box states follow confusion/sweat/shock and rainbow/sadness chains',flush=True)
 p.select_expression(0);settled(0);p.affection=p.hunger=p.energy=100;p.tick();assert p.rules.state==20
 settled(20);expire();settled(0);p.tick();assert p.rules.state==0
 p.panel.grab().save(str(Path(__file__).resolve().parents[1]/'artifacts'/'r7-house-preview.png'))
 print('PASS full stats trigger timed party once; title, subtitle and emotion box render',flush=True)
finally:
 p.tick_timer.stop();p.audio_timer.stop();p.needs_timer.stop();p.click_timer.stop();p.tray.hide();p.panel.hide();p.hide()
 s.clear()
 for k,v in saved.items():s.setValue(k,v)
