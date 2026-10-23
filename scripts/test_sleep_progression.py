"""Sleep stage deadline, cancellation, exact source pixels and real 30s progression."""
import os,sys,time,types
from pathlib import Path
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
import app as module
from app import Pet,ASSETS,ITEMS
from PIL import Image
import numpy as np
app=QApplication([]);app.setQuitOnLastWindowClosed(False)
settings=QSettings('Maorongrong','JellyCat');saved={k:settings.value(k) for k in settings.allKeys()}
pet=Pet();pet.affection=40;pet.hunger=75;pet.energy=80;pet.tick_timer.stop();pet.audio_timer.stop();pet.needs_timer.stop();pet.audio_active=False;pet.roaming=False

def settled(n,timeout=4):
 end=time.monotonic()+timeout
 while pet.transitioning and time.monotonic()<end:QTest.qWait(25)
 assert pet.current_id==n and not pet.transitioning

try:
 assert ITEMS[7]['name']=='酣睡2'
 pet.set_quiet(False);pet.select_expression(5);assert pet.sleep_started_at is None;settled(5)
 assert pet.sleep_started_at is not None
 base=time.monotonic();pet.sleep_started_at=base-29.999;clock=types.SimpleNamespace(monotonic=lambda:base)
 with patch.object(module,'time',clock):
  pet.tick();assert pet.current_id==5
  clock.monotonic=lambda:base+.0011
  pet.tick();assert pet.current_id==8 and pet.transitioning and pet.sleeping
  assert pet.sleep_started_at is None
  assert pet.movie.fileName().endswith('05_to_08.webp')
 settled(8);assert pet.movie.fileName().endswith('08.webp')
 print('PASS 29.999s holds sleep; 30.000s starts direct sleeping-to-sleeping transition',flush=True)
 pet.select_expression(5);settled(5);pet.select_expression(2);assert pet.sleep_started_at is None
 with patch.object(module,'time',types.SimpleNamespace(monotonic=lambda:time.monotonic()+1000)):
  pet.tick();assert pet.current_id==2
 settled(2)
 pet.select_expression(5);assert pet.sleep_started_at is None;settled(5)
 assert 0<=time.monotonic()-pet.sleep_started_at<.2
 pet.set_quiet(True);assert pet.sleep_started_at is None;settled(1)
 print('PASS interrupted/quiet sleep cancels its deadline; new sleep restarts it',flush=True)
 pet.select_expression(8);settled(8);assert pet.sleep_started_at is None
 # Actual wall-clock exercise of the complete uninterrupted sleep cycle.
 pet.select_expression(5);settled(5);started=pet.sleep_started_at
 pet.tick_timer.start(40)
 while pet.current_id==5 and time.monotonic()-started<32:QTest.qWait(20)
 elapsed=time.monotonic()-started
 assert pet.current_id==8 and 30<=elapsed<30.5,elapsed
 assert pet.movie.fileName().endswith('05_to_08.webp')
 pet.tick_timer.stop();settled(8)
 print(f'PASS real continuous sleep advances after {elapsed:.3f}s and stays in sleep2',flush=True)
 # Canonical animation endpoints match their corresponding sleeping loops.
 clip=Image.open(ASSETS/'transitions'/'05_to_08.webp')
 assert clip.n_frames==15
 for frame_index,n in [(0,5),(14,8)]:
  clip.seek(frame_index);actual=np.array(clip.convert('RGBA'))
  expected=np.array(Image.open(ASSETS/'loops'/f'{n:02}.webp').convert('RGBA'))
  assert np.max(np.abs(actual[:,:,3].astype(int)-expected[:,:,3].astype(int)))<=1
  opaque=(actual[:,:,3]>100)&(expected[:,:,3]>100)
  assert np.max(np.abs(actual[:,:,:3][opaque].astype(int)-expected[:,:,:3][opaque].astype(int)))<=1
 print('PASS smooth transition endpoints match sleep1/sleep2; no neutral face inserted',flush=True)
finally:
 pet.tick_timer.stop();pet.needs_timer.stop();pet.audio_timer.stop();pet.click_timer.stop();pet.tray.hide();pet.hide()
 settings.clear()
 for k,v in saved.items():settings.setValue(k,v)
