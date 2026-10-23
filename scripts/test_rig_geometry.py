"""Regressions for continuous tail deformation and anchored puddle breathing."""
import sys,math
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
import process_assets as p
base=p.neutral().resize((640,480),Image.Resampling.LANCZOS)
original=np.array(base)
field=p.tail_influence(base.size)
assert np.max(np.abs(np.diff(field,axis=0)))*3<.8
assert np.max(np.abs(np.diff(field,axis=1)))*3<.8
for k in range(28):
 breathing=np.array(p.breathe(base,k))
 assert np.array_equal(breathing[333:],original[333:]),'puddle base moved during breathing'
 tail=np.array(p.sway_tail(base,k))
 unaffected=field<1e-8
 # Cubic sampling is identity outside the smooth tail field.
 assert np.array_equal(tail[unaffected],original[unaffected]),'pixels outside tail contour moved'
 assert np.array_equal(np.array(p.sway_tail(base,k,base)),original),'static special tail changed'
assert not np.array_equal(np.array(p.sway_tail(base,7)),original)
print('PASS fixed lower body, smooth tail field, exact identity outside tail, static special tails')
# Sleeping fur must preserve the supplied high-resolution PNG's alpha.
sleep=p.sleep_source();reference=Image.open(p.ASSETS/'references'/'sleep-hd.png').convert('RGBA')
alpha=np.array(reference)[:,:,3];alpha[:79,70:190]=0
assert np.array_equal(np.array(sleep)[:,:,3],alpha)
print('PASS sleeping PNG fur alpha preserved exactly, original Z ink separated')
