import sys
sys.path.insert(0,'scripts')
import process_assets as p
from PIL import Image
idle=p.neutral()
for n in (5,8):
 item=p.ITEMS[n-1];hd=p.restore(item);frames=p.animate(hd,item);p.transitions(idle,hd,item,frames);print('restored sleeping fur',n,flush=True)

p.sleep_progression_transition()
