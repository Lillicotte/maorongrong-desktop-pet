from PIL import Image, ImageSequence
import process_assets as p

# New late-authored rigs: repaired sleep and sequential settings ellipsis.
idle=p.neutral()
for item in p.ITEMS:
    if item['id'] in (5,8,13):
        hd=p.restore(item);frames=p.animate(hd,item);p.transitions(idle,hd,item,frames)
        print('updated',item['id'],flush=True)

# Re-export palette GIFs from the lossless masters using the reserved-color fix.
for webp in p.ASSETS.rglob('*.webp'):
    if webp.parent.name not in ('gif','loops','transitions'):continue
    im=Image.open(webp)
    frames=[]
    for f in ImageSequence.Iterator(im):
        frames.extend([f.convert('RGBA').copy()]*max(1,round(f.info.get('duration',80)/80)))
    p.encode(frames,webp.with_suffix('.gif'),write_webp=False)
print('GIF transparency repaired',flush=True)
p.preview()
