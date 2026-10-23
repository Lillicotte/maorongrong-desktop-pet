from PIL import Image,ImageSequence
import process_assets as p
idle=p.neutral()
for item in p.ITEMS:
    n=item['id']
    if n in (3,17,20):continue  # specialized rigs are rebuilt separately
    hd=p.restore(item)
    frames=p.animate(hd,item)
    p.transitions(idle,hd,item,frames)
    print('tail rig',n,flush=True)
