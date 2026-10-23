"""Original-sticker idle rigs, eye blinks, tail sway, and exit melt."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import process_assets as p

def normalized(im):
    canvas=Image.new('RGBA',(640,480))
    canvas.alpha_composite(im.resize((560,391),Image.Resampling.LANCZOS),(40,59))
    return canvas

def smile():
    import cv2
    im=p.clean_source(25)
    pixels=np.array(im);rgb=pixels[:,:,:3].copy();mask=np.zeros(rgb.shape[:2],dtype='uint8')
    # Clear the old wide smile and eyelids locally; retain the original body,
    # ears, tail and surrounding fur instead of pasting a rectangular muzzle.
    cv2.ellipse(mask,(158,169),(25,14),0,0,360,255,-1)
    cv2.ellipse(mask,(303,169),(25,14),0,0,360,255,-1)
    cv2.fillPoly(mask,[np.array([(179,183),(209,186),(238,183),(280,184),(287,207),(277,232),(252,246),(219,248),(194,235),(181,214)],dtype='int32')],255)
    repaired=cv2.inpaint(rgb,mask,4,cv2.INPAINT_TELEA)
    yy,xx=np.mgrid[:rgb.shape[0],:rgb.shape[1]]
    glow=np.exp(-(((xx-235)/115)**2+((yy-193)/100)**2)*1.5)[:,:,None]
    repaired=np.uint8(np.clip(repaired.astype(float)+glow*7,0,255))
    pixels[:,:,:3]=repaired;im=Image.fromarray(pixels)
    from reference_strokes import ink_patch
    ref=Image.open(p.ASSETS/'references'/'idle-smile.png').convert('RGB')
    scale=400/99
    for box in [(29,42,46,56),(66,44,82,57),(43,51,71,63)]:
        x1,y1,x2,y2=box
        patch,_=ink_patch(ref,box,(round((x2-x1)*scale),round((y2-y1)*scale)),photographic=True)
        im.alpha_composite(patch,(round(50+(x1-10)*scale),round(47+(y1-17)*291/72)))

    return im

def tail_loop(base,k):
    return p.sway_tail(p.breathe(base,k,36),k,period=36)


def blink(source):
    # Two eye patches shrink vertically while a source-derived closed eyelid
    # replaces the fully closed phase. All fur and eyelid pixels are original.
    frames=[];rest=p.clean_source(26)
    for openness in (1,.65,.20,0,.20,.65,1):
        f=source.copy()
        for x in (132,280):
            box=(x,137,x+48,192);eye=source.crop(box)
            clean=source.crop((x,197,x+48,227)).resize((48,55),Image.Resampling.BICUBIC)
            m=Image.new('L',(48,55));ImageDraw.Draw(m).ellipse((2,0,45,54),fill=255)
            clean.putalpha(m.filter(ImageFilter.GaussianBlur(3)));f.alpha_composite(clean,(x,137))
            if openness:
                height=max(3,round(55*openness));eye=eye.resize((48,height),Image.Resampling.BICUBIC)
                mask=m.resize((48,height),Image.Resampling.LANCZOS);eye.putalpha(mask)
                f.alpha_composite(eye,(x,165-height//2))
            else:
                lid=rest.crop((x,193,x+48,214))
                lm=Image.new('L',lid.size);ImageDraw.Draw(lm).ellipse((0,0,47,20),fill=255)
                lid.putalpha(lm.filter(ImageFilter.GaussianBlur(2)));f.alpha_composite(lid,(x,155))
        frames.append(normalized(f))
    return frames

def main():
    folder=p.ASSETS/'idles';folder.mkdir(exist_ok=True)
    flat=p.clean_source(13);flat.paste((0,0,0,0),(170,30,287,65))
    sources={'calm':flat,'smile':smile(),'rest':p.clean_source(26),'curious':p.clean_source(23)}
    for name,source in sources.items():
        base=normalized(source);base.save(folder/f'{name}.png')
        frames=[tail_loop(base,k) for k in range(36)]
        p.encode(frames,folder/f'{name}.gif')
        if name in ('calm','curious'):p.encode(blink(source),folder/f'{name}_blink.gif')
        print('idle',name,flush=True)
    folder=p.ASSETS/'exits';folder.mkdir(exist_ok=True)
    base=normalized(p.clean_source(26));frames=[]
    for k in range(34):
        t=k/33;e=p.smooth(t)
        sx=1+.22*e;sy=1-.94*e
        warped=base.resize((round(640*sx),max(1,round(480*sy))),Image.Resampling.BICUBIC)
        warped.putalpha(warped.getchannel('A').point(lambda a:round(a*(1-p.smooth((t-.65)/.35)))))
        canvas=Image.new('RGBA',base.size)
        canvas.alpha_composite(warped,((640-warped.width)//2,round(441*(1-sy))))
        frames.append(canvas)
    p.encode(frames,folder/'melt.gif');print('exit melt',flush=True)

if __name__=='__main__':main()
