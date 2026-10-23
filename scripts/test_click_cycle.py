"""Exercise an actual click and catch transition frames wrapping to frame zero."""
import os,sys,time,json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint,QSettings
from PySide6.QtTest import QTest
from app import Pet

app=QApplication([]);app.setQuitOnLastWindowClosed(False)
settings=QSettings('Maorongrong','JellyCat');saved={k:settings.value(k) for k in settings.allKeys()}
pet=Pet();pet.audio_timer.stop();pet.audio_active=False;pet.roaming=False
pet.affection=80;pet.hunger=75;pet.energy=80
class HeartRNG:
    def choice(self,pool):
        assert 21 in pool,pool
        return 21
pet.rules.rng=HeartRNG()
pet.set_quiet(False);pet.preview_idle('calm');pet.show();QTest.qWait(1000)
events=[];started=time.monotonic()
play=pet.play_clip;express=pet._show_expression
def trace_play(path,callback=None,bridge=True):
    events.append(('clip',path.parent.name,path.stem,round(time.monotonic()-started,3)))
    play(path,callback,bridge)
    movie=pet.movie;seen={'zero':1}
    def frame(i):
        if i==0:
            seen['zero']+=1
            events.append(('wrap',path.parent.name,path.stem,round(time.monotonic()-started,3)))
    movie.frameChanged.connect(frame)
def trace_express(n,*args,**kwargs):
    events.append(('expression',n,round(time.monotonic()-started,3)))
    return express(n,*args,**kwargs)
pet.play_clip=trace_play;pet._show_expression=trace_express
try:
    QTest.mouseClick(pet,Qt.LeftButton,Qt.NoModifier,QPoint(pet.width()//2,round(pet.height()*.64)))
    QTest.qWait(6800)
    print(json.dumps(events,ensure_ascii=False,indent=2),flush=True)
    assert len([e for e in events if e[0]=='expression' and e[1]==21])==1,'one click triggered multiple pats'
    assert not [e for e in events if e[0]=='wrap' and e[1]=='transitions'],'one-shot transition wrapped to its opening frame'
    assert pet.current_id==0 and not pet.transitioning
    assert pet.affection==82
    print('PASS one click: enter once, hold, exit once, return to idle')
    events.clear();before=pet.affection
    QTest.mouseDClick(pet,Qt.LeftButton,Qt.NoModifier,QPoint(pet.width()//2,round(pet.height()*.64)))
    QTest.qWait(6800)
    assert len([e for e in events if e[0]=='expression' and e[1]==21])==1,events
    assert pet.affection==before+2 and pet.current_id==0 and not pet.transitioning
    print('PASS double click is one interaction, with one reward and one transition cycle')
finally:
    pet.tick_timer.stop();pet.needs_timer.stop();pet.audio_timer.stop();pet.tray.hide();pet.hide()
    settings.clear()
    for k,v in saved.items():settings.setValue(k,v)
