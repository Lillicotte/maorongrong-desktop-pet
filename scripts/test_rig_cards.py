"""Window-level mouse dispatch through actual scrolled expression cards."""
import os,sys,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QScrollArea
from PySide6.QtCore import Qt,QSettings
from PySide6.QtTest import QTest
from app import Pet,ITEMS
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
s=QSettings('Maorongrong','JellyCat');saved={k:s.value(k) for k in s.allKeys()}
pet=Pet();pet.affection=40;pet.hunger=75;pet.energy=80;pet.audio_timer.stop();pet.audio_active=False;pet.tick_timer.stop();pet.needs_timer.stop()
try:
 pet.set_quiet(False);pet.open_panel();panel=pet.panel;panel.show();QTest.qWait(100)
 scroll=panel.findChild(QScrollArea)
 for item in ITEMS:
  pet.rules.quiet=False;pet.rules.enter(0,time.monotonic());pet._apply_rules(direct=True)
  n=item['id'];card=panel.cards[n]
  scroll.ensureWidgetVisible(card);QTest.qWait(25)
  point=card.mapTo(panel,card.rect().center())
  assert panel.childAt(point)==card,('card covered by another widget',n)
  QTest.mouseClick(panel.windowHandle(),Qt.LeftButton,Qt.NoModifier,point)
  assert pet.current_id==n and card.isChecked(),('window mouse not delivered',n)
  assert pet.movie.fileName().endswith(f'{n:02}_in.webp'),('manual selection delayed by previous exit',n)
  QTest.qWait(100)
 print('PASS window mouse dispatch to all 26 scrolled cards; newest selection starts immediately')
 # Rapid new selections cancel older clip callbacks; the final card wins.
 for n in (9,2,21,5):pet.select_expression(n);QTest.qWait(50)
 QTest.qWait(1450)
 assert pet.current_id==5 and not pet.transitioning and pet.movie.fileName().endswith('05.webp')
 print('PASS rapid card changes cannot replay stale transitions')
finally:
 pet.tick_timer.stop();pet.needs_timer.stop();pet.audio_timer.stop();pet.tray.hide();panel.hide();pet.hide()
 s.clear()
 for k,v in saved.items():s.setValue(k,v)
