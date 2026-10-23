"""Reference-derived strokes: retain ink contours, variable width and source palette."""
import cv2
import numpy as np
from PIL import Image,ImageFilter

def sharpen_coverage(mask,size,gain=1.65):
    up=cv2.resize(mask.astype('float32'),size,interpolation=cv2.INTER_CUBIC)
    up=np.clip(up,0,1);mass=float(mask.mean()*size[0]*size[1]);lo,hi=0.,1.
    for _ in range(24):
        pivot=(lo+hi)/2;out=np.clip((up-pivot)*gain+.5,0,1)
        if out.sum()>mass:lo=pivot
        else:hi=pivot
    return np.clip((up-(lo+hi)/2)*gain+.5,0,1)

def ink_patch(reference,box,size,photographic=False):
    raw=np.array(reference.convert('RGB'));gray=cv2.cvtColor(raw,cv2.COLOR_RGB2GRAY).astype(float)
    bg=cv2.morphologyEx(gray.astype('uint8'),cv2.MORPH_CLOSE,np.ones((11,11),dtype='uint8')).astype(float)
    x1,y1,x2,y2=box;g=gray[y1:y2,x1:x2];b=bg[y1:y2,x1:x2]
    delta=b-g
    core=g[delta>max(12,float(delta.max())*.6)]
    darkest=float(np.percentile(core,15)) if core.size else float(g.min())
    alpha=np.clip((delta-3)/np.maximum(b-darkest-3,1),0,1)
    if photographic:
        # The photo's blur mixes ink with pale fur. Treat the clear sticker's
        # pigment as the original ink, then undo optical blur on coverage only.
        alpha=np.clip(delta/np.maximum(b-60,1),0,1).astype('float32')
        observed=alpha.copy();estimate=np.maximum(alpha,.001)
        for _ in range(28):
            blurred=cv2.GaussianBlur(estimate,(0,0),1.05)
            estimate*=cv2.GaussianBlur(observed/np.maximum(blurred,.003),(0,0),1.05)
            estimate=np.clip(estimate,0,1)
        alpha=estimate
    # Suppress fur grain while retaining the soft, uneven original brush edge.
    if not photographic:alpha[delta<max(6,float(delta.max())*.15)]=0
    # Keep the actual connected ink stroke; morphological fur shading must not
    # become a rectangular gray patch around the new eye/mouth.
    count,labels,stats,_=cv2.connectedComponentsWithStats((alpha>(.18 if photographic else .5)).astype('uint8'))
    if count>1:
        dominant=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))
        core=(labels==dominant).astype('uint8')
        near=cv2.dilate(core,np.ones((3,3),dtype='uint8'))>0
        alpha*=near
    coverage=sharpen_coverage(alpha,size,gain=3 if photographic else 1.65)
    local=raw[y1:y2,x1:x2];ink=local[delta>float(delta.max())*.75]
    color=np.array([77,52,48]) if photographic else np.median(ink,axis=0) if len(ink) else local.reshape(-1,3)[np.argmin(g)]
    # Gentle source-derived pigment variation instead of a flat vector stroke.
    variance=cv2.resize(g-cv2.GaussianBlur(g,(0,0),1),size,interpolation=cv2.INTER_CUBIC)
    variance=np.clip(variance,-3,3)
    rgb=np.uint8(np.clip(color[None,None,:]+variance[:,:,None],0,255))
    return Image.fromarray(np.dstack([rgb,np.uint8(coverage*255+.5)])),alpha

def reference_fur(im,donor,profile):
    raw=np.array(im);rgb=raw[:,:,:3].astype(float);w,h=im.size
    detail=np.array(donor.resize(im.size,Image.Resampling.LANCZOS))[:,:,:3]
    # Remove every donor facial/highlight mark before borrowing fur frequencies.
    mask=np.zeros((h,w),dtype='uint8')
    sx=w/510;sy=h/356
    for x,y,rx,ry in [(151,169,30,35),(298,169,30,35),(231,192,50,20),(267,112,42,27)]:
        cv2.ellipse(mask,(round(x*sx),round(y*sy)),(round(rx*sx),round(ry*sy)),0,0,360,255,-1)
    detail=cv2.inpaint(detail,mask,6,cv2.INPAINT_TELEA)
    lum=cv2.cvtColor(detail,cv2.COLOR_RGB2GRAY).astype(float)
    grain=(lum-cv2.GaussianBlur(lum,(0,0),1.2))*.7+(lum-cv2.GaussianBlur(lum,(0,0),4))*.65
    grain=np.clip(grain,-12,12)
    yy,xx=np.mgrid[:h,:w];x=xx/w*100;y=yy/h*100
    if profile==3:
        skin=(x>16)&(x<75)&(y>29)&(y<75)
        skin&=~(((x>23)&(x<40)&(y>39)&(y<54))|((x>52)&(x<70)&(y>39)&(y<54))|((x>38)&(x<56)&(y>47)&(y<60)))
        skin&=~((y>59)&(x>25)&(x<70))
        tail=(x>86)&(x<95)&(y>23)&(y<50)
    else:
        skin=(x>16)&(x<77)&(y>31)&(y<79)
        skin&=~(((x>24)&(x<40)&(y>40)&(y<53))|((x>53)&(x<70)&(y>40)&(y<53))|((x>34)&(x<60)&(y>48)&(y<62)))
        tail=(x>87)&(x<94)&(y>33)&(y<59)
    skin=(skin|tail)&(raw[:,:,3]>65)
    donor_alpha=np.array(donor.resize(im.size,Image.Resampling.LANCZOS))[:,:,3]
    distance=cv2.distanceTransform((donor_alpha>220).astype('uint8'),cv2.DIST_L2,5)
    donor_support=np.clip((distance-7)/12,0,1)
    support=cv2.GaussianBlur(skin.astype('float32'),(0,0),3)*skin*donor_support
    rgb+=grain[:,:,None]*support[:,:,None]*1.15
    raw[:,:,:3]=np.uint8(np.clip(rgb,0,255))
    return Image.fromarray(raw)
