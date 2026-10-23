"""Deterministic restoration: original pixels, no generative redraw.
Upscaling improves presentation, not the amount of source information.
"""
from pathlib import Path
import json, math, shutil
from PIL import Image, ImageFilter, ImageDraw, ImageOps
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
ITEMS=json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))

def clean_source(n):
    im=Image.open(ASSETS/'originals'/f'{n:02}.jpg').convert('RGBA')
    # Remove isolated palette debris, while retaining ears, fur and accessories.
    alpha=np.array(im.getchannel('A'));seen=np.zeros(alpha.shape,dtype=bool)
    for y,x in zip(*np.where(alpha>100)):
        if seen[y,x]:continue
        todo=[(y,x)];seen[y,x]=True;component=[]
        while todo:
            yy,xx=todo.pop();component.append((yy,xx))
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny,nx=yy+dy,xx+dx
                if 0<=ny<alpha.shape[0] and 0<=nx<alpha.shape[1] and not seen[ny,nx] and alpha[ny,nx]>100:
                    seen[ny,nx]=True;todo.append((ny,nx))
        if len(component)<(2 if im.width<=100 else 5):
            for yy,xx in component:alpha[yy,xx]=0
    im.putalpha(Image.fromarray(alpha));return im

def sleep_source(n=5):
    # Keep every supplied HD pixel and its fur alpha unchanged. Only the Z ink
    # in the transparent top margin is separated for animation.
    im=Image.open(ASSETS/'references'/('sleep2.png' if n==8 else 'sleep-hd.png')).convert('RGBA')
    im.paste((0,0,0,0),(65,15,175,90) if n==8 else (70,0,190,79))
    return im


def smug_source():
    import cv2
    im=clean_source(13);im.paste((0,0,0,0),(170,30,287,65))
    a=np.array(im);mask=np.zeros(a.shape[:2],dtype='uint8')
    for center,axes in [((151,169),(25,29)),((298,169),(25,29)),((231,192),(43,13))]:
        cv2.ellipse(mask,center,axes,0,0,360,255,-1)
    a[:,:,:3]=cv2.inpaint(a[:,:,:3],mask,4,cv2.INPAINT_TELEA)
    im=Image.fromarray(a)
    # Actual original ink masks retain curve asymmetry, varying thickness and
    # pigment. No hand-authored Bezier curve or rounded uniform-width pen.
    from reference_strokes import ink_patch
    ref=clean_source(2)
    scale=4.05
    for box in [(23,42,36,50),(58,42,71,50),(35,47,57,56)]:
        x1,y1,x2,y2=box
        patch,_=ink_patch(ref,box,(round((x2-x1)*scale),round((y2-y1)*scale)))
        im.alpha_composite(patch,(round(35+x1*scale),round(-17+y1*scale)))
    return im


def smug_effects(size):
    # Preserve the original raster contour, ink width and colors, using the
    # aligned super-resolution master instead of redrawing stars/cloud paths.
    master=Image.open(ASSETS/'restored'/'02-sr.png').convert('RGBA')
    original=clean_source(2)
    polygons=[[(3,48),(8,43),(11,37),(15,44),(20,48),(15,53),(12,60),(8,53)],
              [(72,29),(77,24),(79,16),(83,24),(89,29),(84,34),(80,42),(75,35)],
              [(5,65),(11,62),(15,58),(20,59),(24,65),(31,64),(41,57),(36,68),(28,72),(32,75),(33,83),(27,85),(21,83),(17,79),(12,82),(8,77),(8,74),(5,71)]]
    layers=[]
    for index,points in enumerate(polygons):
        mask=layer_mask(master.size,[[(x*4,y*4) for x,y in points]])
        mask=mask.filter(ImageFilter.GaussianBlur(.5))
        import cv2
        raw=np.array(master);rgb=raw[:,:,:3].astype(float);gray=rgb.mean(axis=2)
        region=np.array(mask)>128
        # Extract cream/blue fill and its original dark ink. In particular,
        # never carry the gray cat/tail pixels surrounding the accessory.
        core=region&(raw[:,:,3]>80)&(((gray>175)&(rgb[:,:,0]+rgb[:,:,1]-2*rgb[:,:,2]>12)) if index<2 else (((gray>130)&(rgb[:,:,2]-rgb[:,:,0]>8)&(rgb[:,:,1]-rgb[:,:,0]>5))|((gray>190)&(rgb[:,:,0]-rgb[:,:,2]<15))))
        count,labels,stats,centers=cv2.connectedComponentsWithStats(core.astype('uint8'))
        if count>1:
            cx,cy=[(11,48),(80,30),(18,70)][index]
            distances=np.linalg.norm(centers[1:]-np.array([cx*4,cy*4]),axis=1)
            chosen=1+int(np.argmin(distances));core=labels==chosen
        distance=cv2.distanceTransform((~core).astype('uint8'),cv2.DIST_L2,5)
        ink=region&(gray<115)&(distance<9)
        if index<2:
            tips=[[(11,38),(14,45),(20,48),(15,52),(12,59),(9,52),(4,49),(9,44)],
                  [(79,17),(82,25),(89,30),(84,35),(80,43),(76,35),(72,31),(76,25)]][index]
            tip_mask=np.array(layer_mask(master.size,[[(x*4,y*4) for x,y in tips]]))>0
            ink|=tip_mask&(gray<135)&(raw[:,:,3]>5)
        matte=(core|ink).astype('uint8')
        matte=cv2.morphologyEx(matte,cv2.MORPH_CLOSE,np.ones((3,3),dtype='uint8'))
        matte=cv2.GaussianBlur(matte.astype('float32'),(0,0),.55)
        if index==2:
            # The tapered gray air jet is part of the original puff, so retain
            # its exact raster shading inside a tightly traced outer contour.
            contour=[(22,66),(28,65),(34,62),(39,58),(38,63),(36,67),(31,70),(26,72),(22,74)]
            jet=np.array(layer_mask(master.size,[[(x*4,y*4) for x,y in contour]]).filter(ImageFilter.GaussianBlur(.6)),dtype=float)/255
            matte=np.maximum(matte,jet)
        alpha=np.uint8(raw[:,:,3]*np.clip(matte,0,1))
        layer=master.copy();layer.putalpha(Image.fromarray(alpha))
        layer=layer.resize((560,560),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',size);canvas.alpha_composite(layer,(31,-15));layers.append(canvas)
    return layers



def faithful_small_source(n):
    """Conservative classical deconvolution; preserve every source alpha pixel."""
    import cv2
    im=clean_source(n);raw=np.array(im,dtype=np.float32)/255
    observed=raw[:,:,:3]*raw[:,:,3:]
    estimate=observed.copy()
    for _ in range(7):
        blurred=cv2.GaussianBlur(estimate,(0,0),.52)
        ratio=observed/np.maximum(blurred,.025)
        estimate*=cv2.GaussianBlur(ratio,(0,0),.52)
        estimate=np.clip(estimate,0,1)
    estimate=observed*.45+estimate*.55
    rgb=np.divide(estimate,raw[:,:,3:],out=np.zeros_like(estimate),where=raw[:,:,3:]>1e-4)
    result=np.array(im);result[:,:,:3]=np.uint8(np.clip(rgb*255,0,255))
    return Image.fromarray(result)


def restored_small_source(n):
    from reference_strokes import reference_fur
    im=Image.open(ASSETS/'restored'/f'{n:02}-sr.png').convert('RGBA')
    im=im.resize((600,600),Image.Resampling.LANCZOS)
    return reference_fur(im,clean_source(13),n)


def restored_flower_source():
    return restored_small_source(3)


def restore(item):
    im=sleep_source(item['id']) if item['id'] in (5,8) else smug_source() if item['id']==2 else restored_flower_source() if item['id']==3 else restored_small_source(17) if item['id']==17 else clean_source(item['id'])
    if item['id'] in (3,17):im=im.crop(im.getchannel('A').getbbox())
    # Sharpen gently before scaling; preserve original colors and fur texture.
    alpha=im.getchannel('A')
    rgb=im.convert('RGB') if item['id'] in (5,8) else im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=.55,percent=45,threshold=4))
    rgb.putalpha(alpha)
    contained=ImageOps.contain(rgb,(1344,968),Image.Resampling.LANCZOS)
    hd=Image.new('RGBA',(1536,1152))
    hd.alpha_composite(contained,((1536-contained.width)//2,1080-contained.height))
    display=hd.copy()
    if item['id']==2:
        for layer in smug_effects((640,480)):display.alpha_composite(layer.resize(display.size,Image.Resampling.LANCZOS))
    if item['id'] in (5,8):display.alpha_composite(zz_layer((640,480),item['id']).resize(display.size,Image.Resampling.LANCZOS))
    display.save(ASSETS/'hd'/f'{item["id"]:02}.png')
    return hd

def motion(n,t):
    s=math.sin(t);c=math.cos(t)
    sx,sy,dx,dy,angle=1+.006*s,1-.009*s,0,0,0
    if n in (5,8,26):sx,sy=1+.004*s,1-.006*s
    elif n in (7,9,15,22):dx=1.4*math.sin(3*t);sx=1+.008*s;sy=1-.010*s
    elif n in (4,6,12,20,21,25):dy=-3*(1-c);sx=1+.009*s;sy=1-.012*s
    elif n in (10,24):dy=1.3*math.sin(2*t);angle=.45*s
    elif n in (14,18,23):angle=.9*s;dy=-1*(1-c)
    elif n in (2,3,17):angle=.45*s;dy=-1.5*(1-c)
    elif n in (16,19):dx=.7*math.sin(2*t)
    return sx,sy,dx,dy,angle

def encode(frames,path,loop=0,write_webp=True):
    # Desktop playback uses lossless RGBA WebP, avoiding GIF palette holes.
    if write_webp:
        frames[0].save(path.with_suffix('.webp'),save_all=True,append_images=frames[1:],
            duration=[80]*len(frames),loop=loop,lossless=True,method=3)
    size=frames[0].size
    # Train one palette on small copies of every frame to keep GIF colors stable.
    sheet=Image.new('RGB',(160*8,120*math.ceil(len(frames)/8)),(235,229,227))
    for k,frame in enumerate(frames):
        thumb=frame.resize((160,120),Image.Resampling.LANCZOS)
        bg=Image.new('RGB',(160,120),(235,229,227));bg.paste(thumb,mask=thumb.getchannel('A'))
        sheet.paste(bg,((k%8)*160,(k//8)*120))
    palette=sheet.quantize(colors=255,method=Image.Quantize.MEDIANCUT)
    pal=palette.getpalette()[:765]+[0,0,0];palette.putpalette(pal)
    dark_index=int(np.argmin(np.sum(np.array(pal[:765]).reshape(-1,3).astype(float)**2,axis=1)))
    encoded=[]
    for frame in frames:
        bg=Image.new('RGB',size,(235,229,227));bg.paste(frame,mask=frame.getchannel('A'))
        q=bg.quantize(palette=palette,dither=Image.Dither.NONE)
        a=np.array(q)
        # Quantization may choose the reserved 256th palette entry for a real
        # dark pixel. Remap it before marking transparent pixels.
        a[a==255]=dark_index
        a[np.array(frame.getchannel('A'))<128]=255
        q=Image.fromarray(a);q.putpalette(pal);q.info['transparency']=255;encoded.append(q)
    encoded[0].save(path,save_all=True,append_images=encoded[1:],duration=80,
        loop=loop,transparency=255,disposal=2,optimize=False)

def neutral():
    source=clean_source(13)
    # Ellipsis lies wholly in the transparent margin; no character pixels erased.
    source.paste((0,0,0,0),(170,30,287,65))
    source=source.resize((1344,938),Image.Resampling.LANCZOS)
    hd=Image.new('RGBA',(1536,1152));hd.alpha_composite(source,(96,142))
    hd.save(ASSETS/'hd'/'00.png')
    return hd

def layer_mask(shape,polygons):
    m=Image.new('L',shape)
    d=ImageDraw.Draw(m)
    for points in polygons:d.polygon(points,fill=255)
    return m

def flame_frames():
    """Separate original fire and tail pixels; warp each gently, never redraw."""
    im=Image.open(ASSETS/'originals'/'09.jpg').convert('RGBA')
    fire=layer_mask(im.size,[[(145,88),(165,49),(184,24),(194,62),(214,28),(220,5),(240,22),(252,56),(264,39),(275,67),(295,40),(306,23),(312,41),(300,68),(322,90)],
      [(31,196),(39,177),(51,165),(57,127),(72,119),(77,80),(87,120),(101,141),(89,178),(79,228),(52,235)]])
    tail=layer_mask(im.size,[[(351,55),(391,36),(452,52),(482,83),(446,148),(443,205),(418,245),(390,257),(372,229),(384,204),(395,164),(384,131),(363,111)]])
    ImageDraw.Draw(tail).rectangle((438,0,509,280),fill=255)
    # Only existing alpha is used, so polygon margins remain transparent.
    original_alpha=np.array(im.getchannel('A'))
    fire.putdata(np.minimum(np.array(fire),original_alpha).flatten())
    tail.putdata(np.minimum(np.array(tail),original_alpha).flatten())
    f=im.copy();f.putalpha(fire)
    # The original fire sticker draws several overlapping tails as a motion
    # smear. Replace that smear with one existing clean tail from sticker 01.
    clean=clean_source(1)
    single=layer_mask(clean.size,[[(377,35),(456,35),(456,162),(438,218),(411,257),(389,261),(380,242),(391,211),(399,167),(387,129),(380,96)]])
    single_a=np.minimum(np.array(single),np.array(clean.getchannel('A')))
    tail_img=clean.copy();tail_img.putalpha(Image.fromarray(single_a))
    body=im.copy();body.putalpha(Image.fromarray(np.maximum(0,original_alpha.astype(int)-np.maximum(np.array(fire),np.array(tail)).astype(int)).astype('uint8')))
    frames=[]
    for k in range(28):
        t=2*math.pi*k/28
        canvas=Image.new('RGBA',im.size)
        fl=f.transform(im.size,Image.Transform.AFFINE,(1,.014*math.sin(t),-2*math.sin(t),0,1+.014*math.sin(2*t),-1.1*math.sin(2*t)),Image.Resampling.BICUBIC)
        ta=tail_img.rotate(6*math.sin(2*t),Image.Resampling.BICUBIC,center=(389,245))
        canvas.alpha_composite(fl);canvas.alpha_composite(ta);canvas.alpha_composite(body)
        big=Image.new('RGBA',(1536,1152));big.alpha_composite(canvas.resize((1344,938),Image.Resampling.LANCZOS),(96,142))
        frames.append(big.resize((640,480),Image.Resampling.LANCZOS))
    return frames

def remap_rgba(frame,dx,dy):
    """Continuous inverse warp in premultiplied RGBA; no cut/paste borders."""
    import cv2
    data=np.asarray(frame,dtype=np.float32)/255
    data[:,:,:3]*=data[:,:,3:]
    yy,xx=np.mgrid[:frame.height,:frame.width].astype('float32')
    warped=cv2.remap(data,xx-np.asarray(dx,dtype='float32'),yy-np.asarray(dy,dtype='float32'),
                     cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    warped=np.clip(warped,0,1)
    warped[:,:,:3]=np.divide(warped[:,:,:3],warped[:,:,3:],out=np.zeros_like(warped[:,:,:3]),where=warped[:,:,3:]>1e-6)
    result=np.uint8(np.clip(warped*255+.5,0,255))
    # Exact identity wherever the deformation is zero, including the puddle.
    identity=(np.abs(dx)+np.abs(dy))<1e-6
    result[identity]=np.array(frame)[identity]
    return Image.fromarray(result)


def breathe(frame,k,period=28):
    yy,xx=np.mgrid[:frame.height,:frame.width]
    # All pixels at/below the puddle's shoulder remain exactly stationary.
    height=np.clip((333-yy)/245,0,1)**1.7
    body=np.exp(-((xx-295)/185)**6)*np.clip((475-xx)/50,0,1)**2
    phase=math.sin(math.tau*k/period)
    dy=-2.1*phase*height*body
    dx=(xx-295)/180*.65*phase*height*body
    return remap_rgba(frame,dx,dy)


def tail_influence(size):
    # Feathered silhouette follows ONLY the furry tail, with a fixed root.
    import cv2
    points=[(380,238),(393,210),(393,176),(382,143),(381,108),(388,78),
            (403,55),(428,43),(450,45),(453,68),(431,86),(421,108),
            (420,134),(427,163),(428,188),(417,224),(400,252)]
    m=layer_mask(size,[[(40+x*560/510,59+y*391/356) for x,y in points]])
    mask=np.array(m,dtype='float32')/255
    mask=cv2.GaussianBlur(cv2.dilate(mask,np.ones((9,9),dtype='uint8')),(0,0),2)
    yy,xx=np.mgrid[:size[1],:size[0]]
    root=np.clip((335-yy)/130,0,1)**1.8
    return mask*root


def small_tail_influence(n,size):
    import cv2
    source=clean_source(n);bbox=source.getchannel('A').getbbox()
    w,h=bbox[2]-bbox[0],bbox[3]-bbox[1];factor=min(560/w,403/h)
    ox=(640-w*factor)/2-bbox[0]*factor;oy=450-h*factor-bbox[1]*factor
    points=([(80,62),(82,54),(80,43),(82,30),(86,22),(92,18),(97,20),(98,25),(91,33),(89,40),(93,51),(93,59),(88,69),(80,72)] if n==3 else
            [(82,65),(85,55),(81,42),(82,30),(88,23),(92,24),(97,27),(96,34),(90,39),(94,50),(95,62),(90,70),(83,75)])
    mask=np.array(layer_mask(size,[[(ox+x*factor,oy+y*factor) for x,y in points]]),dtype='float32')/255
    mask=cv2.GaussianBlur(cv2.dilate(mask,np.ones((7,7),dtype='uint8')),(0,0),3)
    yy,xx=np.mgrid[:size[1],:size[0]]
    return mask*np.clip((oy+75*factor-yy)/(45*factor),0,1)**1.6


def sway_tail(frame,k,static_source=None,period=28,amplitude=3,profile=None):
    if static_source is not None:return frame
    influence=small_tail_influence(profile,frame.size) if profile else tail_influence(frame.size)
    dx=influence*amplitude*math.sin(math.tau*k/period)
    return remap_rgba(frame,dx,np.zeros_like(dx))


def effect_layers(base,n):
    """Masks use original sticker coordinates; expression and effects stay separate."""
    sx=1344/510*640/1536;ox=96*640/1536;oy=142*480/1152
    m=Image.new('L',base.size);d=ImageDraw.Draw(m)
    def poly(points):d.polygon([(round(ox+x*sx),round(oy+y*sx)) for x,y in points],fill=255)
    if n==24:
        poly([(140,171),(169,174),(167,207),(170,240),(164,274),(131,277),(137,242),(134,210)])
        poly([(292,172),(322,178),(324,214),(327,250),(323,275),(290,274),(292,238),(287,205)])
    elif n==21:
        poly([(26,31),(135,33),(130,123),(76,133),(25,91)])
        poly([(370,77),(445,77),(445,153),(370,153)])
        poly([(45,190),(130,190),(137,250),(84,270),(43,240)])
    elif n==12:poly([(20,0),(130,0),(130,145),(95,167),(20,167)])
    elif n==4:poly([(30,88),(104,88),(104,185),(30,185)])
    elif n==18:poly([(45,10),(338,10),(338,107),(136,85),(106,200),(45,200)])
    elif n==20:
        # Confetti in the transparent margin, avoiding the hat/head and bow.
        poly([(15,0),(194,0),(194,45),(120,78),(84,155),(15,155)])
        poly([(278,0),(486,0),(486,160),(452,160),(419,85),(335,82),(278,45)])
    else:return base.copy(),None,None
    m=m.filter(ImageFilter.GaussianBlur(.5))
    mask=np.array(m,dtype=np.uint16)
    pixels=np.array(base);alpha=pixels[:,:,3].astype(np.uint16)
    if n==24:
        # The polygon only limits the search. Extract actual blue water, never
        # the gray face pixels inside a bounding region.
        rgb=pixels[:,:,:3].astype(float)
        blue=np.minimum(rgb[:,:,2]-rgb[:,:,0]-4,rgb[:,:,1]-rgb[:,:,0]-3)
        coverage=np.clip(blue/8,0,1)
        mask=np.uint16(mask*coverage)
    effects=base.copy();effects.putalpha(Image.fromarray((alpha*mask//255).astype('uint8')))
    body=base.copy();body.putalpha(Image.fromarray((alpha*(255-mask)//255).astype('uint8')))
    if n==24:
        import cv2
        # Water lies inside the existing opaque face. Inpaint its original
        # footprint instead of putting a donor's open eyes behind the tears.
        pixels=np.array(base)
        fill=np.uint8(mask>10)*255
        pixels[:,:,:3]=cv2.inpaint(pixels[:,:,:3],fill,6,cv2.INPAINT_TELEA)
        repaired=Image.fromarray(pixels)
        return repaired,effects,m
    # Fill only the character surface previously covered by accessories.
    donor=Image.open(ASSETS/'hd'/'00.png').resize(base.size,Image.Resampling.LANCZOS)
    da=np.array(donor.getchannel('A'),dtype=np.uint16)
    donor.putalpha(Image.fromarray((da*mask//255).astype('uint8')))
    donor.alpha_composite(body)
    return donor,effects,m

def zz_layer(size,n=5):
    source=Image.open(ASSETS/'references'/('sleep2.png' if n==8 else 'sleep-hd.png')).convert('RGBA')
    box=(65,15,175,90) if n==8 else (70,0,190,79)
    z=Image.new('RGBA',source.size)
    z.alpha_composite(source.crop(box),box[:2])
    # Use the actual ink/alpha from the supplied PNG; no substitute font.
    frame=Image.new('RGBA',(640,480))
    frame.alpha_composite(z.resize((560,391),Image.Resampling.LANCZOS),(40,59))
    return frame.resize(size,Image.Resampling.LANCZOS)


def effect_frame(body,effect,n,k,amount=1):
    result=body.copy()
    if effect is None:return result
    t=2*math.pi*k/28
    layer=effect.copy()
    if n==24:
        import cv2
        # Flow only the original water's internal shading. Its gray-blue ink
        # border and eyelid anchors remain fixed, with a seamless periodic tile.
        raw=np.array(effect);flow=raw.copy();alpha=raw[:,:,3]
        distance=cv2.distanceTransform((alpha>120).astype('uint8'),cv2.DIST_L2,5)
        for x in np.where((alpha>120).any(axis=0))[0]:
            rows=np.where(alpha[:,x]>120)[0]
            if len(rows)<8:continue
            top,bottom=rows[0],rows[-1];span=bottom-top+1
            y=np.arange(top,bottom+1)
            profile=np.stack([np.interp(y,rows,raw[rows,x,c]) for c in range(3)],axis=1)
            low=cv2.GaussianBlur(profile.astype('float32'),(1,0),7)
            detail=profile-low
            # Remove the endpoint difference so the wrapping texture has no cut.
            detail-=np.linspace(detail[0],detail[-1],span)
            pos=(y-top-k/28*span)%span
            shifted=np.stack([np.interp(pos,np.arange(span+1),np.r_[detail[:,c],detail[0,c]]) for c in range(3)],axis=1)
            edge=np.clip((distance[y,x]-1)/3,0,1)
            root=np.clip((y-top)/12,0,1)*np.clip((bottom-y)/10,0,1)
            adjusted=raw[y,x,:3]+(shifted-detail)*(edge*root)[:,None]*1.3
            flow[y,x,:3]=np.uint8(np.clip(adjusted,0,255))
        layer=Image.fromarray(flow)
    elif n==21:
        layer=layer.transform(layer.size,Image.Transform.AFFINE,(1,0,-1.3*math.sin(t),0,1,4*math.sin(t)),Image.Resampling.BICUBIC)
    elif n==12:
        layer=layer.rotate(2*math.sin(t),Image.Resampling.BICUBIC,center=(115,120))
        amount*=.48+.52*(.5+.5*math.cos(2*t))
    elif n in (5,8):layer=layer.rotate(3*math.sin(t),Image.Resampling.BICUBIC,center=(135,70))
    elif n==4:amount*=.7+.3*(.5+.5*math.sin(t))
    else:layer=layer.transform(layer.size,Image.Transform.AFFINE,(1,0,math.sin(t),0,1,2*math.sin(t)),Image.Resampling.BICUBIC)
    layer.putalpha(layer.getchannel('A').point(lambda a:round(a*amount)))
    result.alpha_composite(layer);return result

def dots_frames(base):
    body=base.copy();scale=1344/510*640/1536;ox=40;oy=142*480/1152
    boxes=[]
    for x in (188,230,272):
        box=(round(ox+(x-12)*scale),round(oy+34*scale),round(ox+(x+12)*scale),round(oy+62*scale))
        boxes.append(box);body.paste((0,0,0,0),box)
    active=[(),(0,),(0,1),(0,1,2),(1,2),(2,),()]
    frames=[]
    for k in range(28):
        f=body.copy()
        for i in active[k//4]:f.alpha_composite(base.crop(boxes[i]),boxes[i][:2])
        frames.append(f)
    return frames

def animate(hd,item):
    n=item['id'];base=hd.resize((640,480),Image.Resampling.LANCZOS)
    body,effect,_=effect_layers(base,n)
    if n in (5,8):effect=zz_layer(base.size,n)
    frames=[]
    for k in range(28):
        frame=breathe(body,k)
        if n not in (7,18,9,17):frame=sway_tail(frame,k)
        if n==2:
            for i,layer in enumerate(smug_effects(base.size)):
                if i<2:
                    a=.55+.45*(.5+.5*math.sin(math.tau*k/28+i))
                    layer.putalpha(layer.getchannel('A').point(lambda v:round(v*a)))
                else:layer=layer.transform(layer.size,Image.Transform.AFFINE,(1,0,-1.2*math.sin(math.tau*k/28),0,1,2.8*math.sin(math.tau*k/28)),Image.Resampling.BICUBIC)
                frame.alpha_composite(layer)
        else:frame=effect_frame(frame,breathe(effect,k) if n==24 else effect,n,k)
        frames.append(frame)
    if n==9:frames=flame_frames()
    if n==13:frames=[sway_tail(breathe(f,k),k) for k,f in enumerate(dots_frames(base))]
    encode(frames,ASSETS/'loops'/f'{n:02}.gif')
    return frames


def blend(a,b,weight):
    aa=np.array(a).astype(float)/255;bb=np.array(b).astype(float)/255
    if isinstance(weight,np.ndarray):weight=weight[:,:,None]
    alpha=aa[:,:,3:]*(1-weight)+bb[:,:,3:]*weight
    color=aa[:,:,:3]*aa[:,:,3:]*(1-weight)+bb[:,:,:3]*bb[:,:,3:]*weight
    color=np.divide(color,alpha,out=np.zeros_like(color),where=alpha>0)
    return Image.fromarray(np.uint8(np.clip(np.concatenate([color,alpha],axis=2)*255,0,255)))

def smooth(x):return min(1,max(0,x))**2*(3-2*min(1,max(0,x)))

def transitions(idle,hd,item,frames):
    idle=idle.resize((640,480),Image.Resampling.LANCZOS)
    target=hd.resize((640,480),Image.Resampling.LANCZOS)
    if item['id']==13:target=dots_frames(target)[0]
    body,effect,_=effect_layers(target,item['id'])
    if item['id'] in (5,8):body=target;effect=zz_layer(target.size,item['id'])
    if item['id']==2:
        effect=Image.new('RGBA',target.size)
        for layer in smug_effects(target.size):effect.alpha_composite(layer)
    incoming=[]
    # Eye and mouth timings are authored per expression, not one global fade.
    profiles={
      1:(.05,.38,.35,.62),2:(.02,.36,.18,.52),3:(.10,.40,.20,.48),
      4:(0,.30,.17,.38),5:(0,.42,.22,.42),6:(.10,.32,.15,.55),
      7:(0,.27,.15,.43),8:(0,.42,.22,.42),9:(0,.35,.13,.48),
      10:(.05,.46,.24,.52),11:(.02,.52,.36,.54),12:(0,.28,.17,.32),
      13:(.08,.48,.30,.55),14:(.12,.45,.35,.48),15:(0,.33,.18,.48),
      16:(.05,.34,.28,.50),17:(0,.52,.15,.50),18:(0,.24,.12,.38),
      19:(.05,.32,.21,.50),20:(0,.38,.14,.40),21:(0,.28,.14,.33),
      22:(0,.38,.17,.42),23:(.05,.32,.28,.46),24:(0,.40,.18,.52),
      25:(0,.38,.15,.48),26:(0,.62,.30,.54)}
    eye_delay,eye_time,mouth_delay,mouth_time=profiles[item['id']]
    for k in range(15):
        t=k/14
        w=np.full((480,640),smooth(t),dtype=float)
        def rect(x1,y1,x2,y2,delay,duration):
            x1,x2=[round((96+x*1344/510)*640/1536) for x in (x1,x2)]
            y1,y2=[round((142+y*938/356)*480/1152) for y in (y1,y2)]
            w[y1:y2,x1:x2]=smooth((t-delay)/duration)
        rect(120,130,335,190,eye_delay,eye_time)
        rect(165,190,295,260,mouth_delay,mouth_time)
        if effect is not None:
            # Complete eyes/mouth before fading in the separate accessory layer.
            face_w=np.full((480,640),smooth(min(1,t/.5)))
            # w already contains expression-specific local timing; accelerate
            # this face-only phase to make room for the delayed effect.
            face_w=np.maximum(face_w,w)
            face=blend(idle,body,face_w)
            incoming.append(effect_frame(face,effect,item['id'],k,smooth((t-.53)/.47)))
        else:incoming.append(blend(idle,target,w))
    outgoing=[blend(frames[0],idle,smooth(k/8)) for k in range(9)]
    encode(incoming,ASSETS/'transitions'/f'{item["id"]:02}_in.gif')
    encode(outgoing,ASSETS/'transitions'/f'{item["id"]:02}_out.gif')
    if item['kind']=='action':
        exported=incoming+[frames[k%len(frames)] for k in range(38)]+outgoing
    else:exported=frames
    encode(exported,ASSETS/'gif'/f'{item["id"]:02}_{item["name"]}.gif')

def sleep_progression_transition():
    # Both endpoints are sleeping images, with the original Z ink included.
    # Never insert the neutral face between sleep stages.
    endpoints=[]
    for n in (5,8):
        hd=restore(ITEMS[n-1]);frame=hd.resize((640,480),Image.Resampling.LANCZOS)
        frame.alpha_composite(zz_layer(frame.size,n));endpoints.append(frame)
    frames=[blend(endpoints[0],endpoints[1],smooth(k/14)) for k in range(15)]
    encode(frames,ASSETS/'transitions'/'05_to_08.gif')
    return frames


def preview():
    sheet=Image.new('RGB',(1200,7*225),(247,242,238));d=ImageDraw.Draw(sheet)
    from PIL import ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    for idx,item in enumerate(ITEMS):
        im=Image.open(ASSETS/'hd'/f'{item["id"]:02}.png').resize((290,218),Image.Resampling.LANCZOS)
        x=(idx%4)*300;y=(idx//4)*225
        sheet.paste(im,(x,y-7),im)
        d.text((x+100,y+200),f'{item["id"]:02} {item["name"]}',font=font,fill='#66515e')
    sheet.save(ROOT/'素材总览.jpg',quality=93)

if __name__=='__main__':
    for folder in ('hd','gif','loops','transitions'): (ASSETS/folder).mkdir(exist_ok=True)
    actions={4,6,12,17,18,19,21,23,25}
    for item in ITEMS:item['kind']='action' if item['id'] in actions else 'state'
    (ASSETS/'manifest.json').write_text(json.dumps(ITEMS,ensure_ascii=False,indent=2),encoding='utf-8')
    idle=neutral();idle_frames=animate(idle,{'id':0})
    encode(idle_frames,ASSETS/'gif'/'00_常态.gif')
    for item in ITEMS:
        hd=restore(item);frames=animate(hd,item);transitions(idle,hd,item,frames);print(f'{item["id"]:02} {item["name"]} {item["kind"]}',flush=True)
    sleep_progression_transition();preview()

