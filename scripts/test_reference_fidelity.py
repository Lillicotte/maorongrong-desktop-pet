"""Reference stroke/alpha fidelity and independent liquid-flow regressions."""
import sys,json
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
import process_assets as p
from reference_strokes import ink_patch
report={}
ref=p.clean_source(2)
for label,box in [('left_eye',(23,42,36,50)),('right_eye',(58,42,71,50)),('mouth',(35,47,57,56))]:
 x1,y1,x2,y2=box;scale=4.05
 patch,reference=ink_patch(ref,box,(round((x2-x1)*scale),round((y2-y1)*scale)))
 out=np.array(patch)[:,:,3]/255
 def centroid(mask):
  yy,xx=np.mgrid[:mask.shape[0],:mask.shape[1]]
  return np.array([(xx*mask).sum()/mask.sum(),(yy*mask).sum()/mask.sum()])
 # The reconstruction is scaled at pixel centers, with no pen-path replacement.
 expected=(centroid(reference)+.5)*np.array([out.shape[1]/reference.shape[1],out.shape[0]/reference.shape[0]])-.5
 error=np.linalg.norm(centroid(out)-expected)/scale
 assert error<.35,(label,error)
 ratio=out.mean()/reference.mean()
 assert .94<ratio<1.06,(label,ratio)
 report[label]={'centroid_error_source_pixels':round(float(error),4),'ink_coverage_ratio':round(float(ratio),4)}
print('PASS original smug ink curve placement and coverage preserved')
reference=Image.open(p.ASSETS/'references'/'sleep-hd.png').convert('RGBA')
original=np.array(reference)[:,:,3];original[:79,70:190]=0
assert np.array_equal(np.array(p.sleep_source())[:,:,3],original)
exact=np.array(reference);exact[:79,70:190]=0
assert np.array_equal(np.array(p.sleep_source()),exact)
print('PASS exact high-resolution sleeping pixels, ink and fur alpha')
for n in (3,17):
 expected=np.array(Image.open(p.ASSETS/'restored'/f'{n:02}-sr.png').convert('RGBA').resize((600,600),Image.Resampling.LANCZOS))[:,:,3]
 actual=np.array(p.restored_small_source(n))[:,:,3]
 assert np.array_equal(expected,actual),(n,'reference texture changed silhouette')
print('PASS flower/music detail restoration leaves supplied transparency unchanged')
base=Image.open(p.ASSETS/'hd'/'24.png').convert('RGBA').resize((640,480),Image.Resampling.LANCZOS)
body,effect,_=p.effect_layers(base,24)
frames=[np.array(p.effect_frame(body,effect,24,k)) for k in range(29)]
assert np.array_equal(frames[0],frames[28]),'water flow cycle does not close'
outside=np.array(effect)[:,:,3]==0
assert all(np.array_equal(frame[outside],frames[0][outside]) for frame in frames),'tear animation moved face pixels'
assert np.count_nonzero(np.any(frames[0]!=frames[7],axis=2))>300,'water is static'
assert all(np.array_equal(frame[:,:,3],frames[0][:,:,3]) for frame in frames),'tear outline/opacity changed'
print('PASS tears flow internally, face/outline fixed, seamless repeat')
report['tears']={'cycle_closes':True,'face_static':True,'opacity_static':True}
(p.ROOT/'artifacts'/'reference-fidelity-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
