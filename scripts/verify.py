import sys,os,math,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageSequence
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QSettings
from app import Pet,ITEMS,ASSETS
from audio_monitor import AudioMonitor
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
s=QSettings('Maorongrong','JellyCat');backup={k:s.value(k) for k in s.allKeys()}
pet=Pet();pet.audio_timer.stop();pet.audio_active=False
pet.affection=40;pet.hunger=75;pet.energy=80
def wait_for(fn,timeout=8):
    end=time.monotonic()+timeout
    while not fn() and time.monotonic()<end:QTest.qWait(30)
    assert fn(),'timed out'
try:
    pet.set_quiet(False);pet.open_panel()
    for item in ITEMS:
        im=Image.open(ASSETS/'gif'/f'{item["id"]:02}_{item["name"]}.gif')
        assert im.size==(640,480) and im.info.get('loop')==0
        assert Image.open(ASSETS/'loops'/f'{item["id"]:02}.webp').mode=='RGBA'
        if item['kind']=='action':
            total=sum(f.info.get('duration',80) for f in ImageSequence.Iterator(im))
            assert 4600<=total<=5400,(item,total)
        # Exercise each card from an unlocked state; anger lock is tested separately.
        pet.rules.quiet=False;pet.rules.enter(0,time.monotonic());pet._apply_rules(direct=True)
        pet.panel.cards[item['id']].click()
        assert pet.current_id==item['id'] and pet.movie.isValid() and pet.panel.cards[item['id']].isChecked(),item
    print('PASS 26 full-card clicks, selection, lossless clips, five-second GIFs',flush=True)
    pet.panel.size_value.setValue(420);assert pet.width()==420 and pet.panel.slider.value()==420
    pet.set_size(240);assert pet.panel.size_value.value()==240
    print('PASS size controls synchronized',flush=True)
    pet.select_expression(0);wait_for(lambda:not pet.transitioning)
    t=time.monotonic();pet.select_expression(4);wait_for(lambda:pet.current_id==0 and not pet.transitioning)
    elapsed=time.monotonic()-t;assert 4.3<=elapsed<=6,elapsed
    print(f'PASS short action transitions finish in {elapsed:.2f}s',flush=True)
    pet.set_quiet(True);wait_for(lambda:not pet.transitioning);pos=pet.pos()
    pet.pat();pet.feed();pet.play();pet.sleep_toggle();pet.home();pet.next_walk=0
    for _ in range(50):pet.tick()
    assert pet.current_id==1 and pet.pos()==pos and pet.home_target is None
    print('PASS quiet blocks expression changes and movement',flush=True)
    pet.select_expression(9);wait_for(lambda:not pet.transitioning);pos=pet.pos();pet.next_walk=0
    for _ in range(50):pet.tick()
    assert pet.pos()==pos and math.isinf(pet.until)
    print('PASS persistent states never wander',flush=True)
    pet.select_expression(0);wait_for(lambda:not pet.transitioning)
    pet.move(100,100);pet.walk_position=[100.,100.];pet.velocity=(.4,.3)
    pet.walk_until=time.monotonic()+5;pet.next_walk=time.monotonic()+80
    for _ in range(30):pet.tick()
    assert pet.x()>100 and pet.y()>100 and pet.moving
    start=pet.pos();pet.home();target=pet.home_target;assert pet.pos()==start
    pet.tick();assert pet.pos()!=start and pet.pos()!=target
    for _ in range(200):pet.tick()
    assert pet.home_target is None and (pet.pos()-target).manhattanLength()<=1
    print('PASS two-axis crawl and animated return path',flush=True)
    pet.panel.tabs.setCurrentIndex(1);assert pet.current_id==13 and pet.panel.setting_movie.isValid()
    pet.panel.tabs.setCurrentIndex(0);pet.roaming=False
    for key in ('calm','smile','rest','curious'):
        pet.preview_idle(key);wait_for(lambda:not pet.transitioning);assert key in pet.movie.fileName()
        if key in ('calm','curious'):
            pet.next_blink=0;pet.tick();assert '_blink' in pet.movie.fileName()
            QTest.qWait(850);assert '_blink' not in pet.movie.fileName()
    print('PASS settings ellipsis, four idle faces, occasional blinks',flush=True)
    class FakeMeter:
        def poll(self):return True
    pet.audio_monitor=FakeMeter();pet.update_audio()
    assert pet.audio_active and '17.webp' in pet.movie.fileName()
    pet.set_quiet(True);pet.update_audio();assert pet.current_id==1
    real=AudioMonitor();peak=real.peak();assert 0<=peak<=1
    print(f'PASS audio switching and quiet priority, endpoint available={real.available}',flush=True)
    im=Image.open(ASSETS/'exits'/'melt.webp');im.seek(im.n_frames-1)
    assert im.convert('RGBA').getchannel('A').getextrema()==(0,0)
    print('PASS exit melt becomes fully transparent',flush=True)
finally:
    pet.tick_timer.stop();pet.needs_timer.stop();pet.audio_timer.stop();pet.tray.hide()
    if pet.panel:pet.panel.hide()
    pet.hide();s.clear()
    for k,v in backup.items():s.setValue(k,v)
