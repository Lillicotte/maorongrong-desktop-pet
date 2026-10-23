"""Rebuild only the corrected reference assets and their animation clips."""
import process_assets as p
import build_idles as idle
import build_special_effects as special
from PIL import Image
base=p.neutral()
for n in (2,5,8,24):
 item=p.ITEMS[n-1];hd=p.restore(item);frames=p.animate(hd,item);p.transitions(base,hd,item,frames)
 print('updated',n,flush=True)
for n in (3,17):
 item=p.ITEMS[n-1];hd=p.restore(item)
 frames=special.floating(n) if n==3 else special.music()
 p.encode(frames,p.ASSETS/'loops'/f'{n:02}.gif');p.transitions(base,hd,item,frames)
 print('updated',n,flush=True)
source=idle.smile();normal=idle.normalized(source);normal.save(p.ASSETS/'idles'/'smile.png')
p.encode([idle.tail_loop(normal,k) for k in range(36)],p.ASSETS/'idles'/'smile.gif')
p.preview();print('updated smile idle and overview',flush=True)

p.sleep_progression_transition()
