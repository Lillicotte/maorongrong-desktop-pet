import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import process_assets as p

def component_effects(source,maximum):
    a=np.array(source.getchannel('A'));seen=np.zeros(a.shape,dtype=bool);mask=np.zeros(a.shape,dtype='uint8')
    for y,x in zip(*np.where(a>128)):
        if seen[y,x]:continue
        todo=[(y,x)];seen[y,x]=True;points=[]
        while todo:
            yy,xx=todo.pop();points.append((yy,xx))
            for dy,dx in ((0,-1),(0,1),(-1,0),(1,0)):
                ny,nx=yy+dy,xx+dx
                if 0<=ny<a.shape[0] and 0<=nx<a.shape[1] and not seen[ny,nx] and a[ny,nx]>128:
                    seen[ny,nx]=True;todo.append((ny,nx))
        if 2<=len(points)<=maximum:
            for yy,xx in points:mask[yy,xx]=a[yy,xx]
    return Image.fromarray(mask)

def to_frame(source):
    cropped=source.crop(p.clean_source(3 if source.width==100 else 20).getchannel('A').getbbox()) if source.width==100 else source
    contained=p.ImageOps.contain(cropped,(560,403),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(640,480));canvas.alpha_composite(contained,((640-contained.width)//2,450-contained.height))
    return canvas


def floating(n):
    import cv2
    source=p.restored_flower_source() if n==3 else p.clean_source(n)
    if n==3:
        # Work larger before separation, keeping the actual 100px silhouette,
        # ties, face and bouquet. No generated body or substituted pose.
        source=source.resize((600,600),Image.Resampling.LANCZOS)
        source=source.filter(ImageFilter.UnsharpMask(1.5,100,4))
        rgb=np.array(source);hsv=cv2.cvtColor(rgb[:,:,:3],cv2.COLOR_RGB2HSV)
        yy,xx=np.mgrid[:600,:600]
        colored=(hsv[:,:,1]>95)&(rgb[:,:,3]>70)
        allowed=(yy<120)|((xx<110)&(yy<440))|((xx>520)&(yy<300))|((xx>480)&(yy>420))
        selected=colored&allowed&((hsv[:,:,0]<35)|(hsv[:,:,0]>160)|(yy<120)|((xx>520)&(yy>430)))
        count,labels,stats,_=cv2.connectedComponentsWithStats(selected.astype('uint8'))
        mask=np.zeros((600,600),dtype='uint8')
        for j in range(1,count):
            if stats[j,cv2.CC_STAT_AREA]>20:mask[labels==j]=255
        mask=cv2.dilate(mask,np.ones((9,9),dtype='uint8'))
    else:mask=np.array(component_effects(source,1800))
    # Each complete petal/confetti component moves as a unit; no column slicing.
    count,labels,stats,_=cv2.connectedComponentsWithStats((mask>0).astype('uint8'))
    parts=[]
    for j in range(1,count):
        if stats[j,cv2.CC_STAT_AREA]<3:continue
        m=np.uint8(labels==j)*255
        layer=source.copy();layer.putalpha(Image.fromarray(np.minimum(m,np.array(source.getchannel('A')))))
        parts.append(layer)
    pixels=np.array(source);original_alpha=pixels[:,:,3].copy()
    # Reconstruct occluded fur locally BEFORE moving effects. At an outer edge,
    # restore the source body's contour rather than filling transparent margin.
    repair=(mask>0).astype('uint8')*255
    pixels[:,:,:3]=cv2.inpaint(pixels[:,:,:3],repair,7,cv2.INPAINT_TELEA)
    if n==3:
        bodymask=Image.new('L',source.size)
        ImageDraw.Draw(bodymask).polygon([(105,135),(180,177),(255,177),(350,174),(436,128),(448,296),(471,355),(530,421),(505,457),(430,471),(320,482),(190,473),(87,475),(36,455),(30,424),(60,365),(90,290)],fill=255)
        # Rebuild the original tail surface under the right-side red petal too.
        ImageDraw.Draw(bodymask).polygon([(498,156),(516,126),(552,108),(582,126),(582,156),(540,198),(534,240),(552,294),(558,348),(528,408),(492,420),(480,378),(504,324),(498,270)],fill=255)
        bodyalpha=np.array(bodymask.filter(ImageFilter.GaussianBlur(1)))
        pixels[:,:,3]=np.where(mask>0,bodyalpha,original_alpha)
        # Reference fur is restored only in the originally occluded pixels;
        # it never changes the supplied silhouette, face, ties or bouquet.
        donor=p.clean_source(13)
        texture=Image.new('RGBA',source.size)
        texture.alpha_composite(donor.resize((638,425),Image.Resampling.LANCZOS),(-32,76))
        texture.alpha_composite(donor.crop((377,40,455,255)).resize((120,340),Image.Resampling.LANCZOS),(480,100))
        donor_data=np.array(texture);donor_rgb=donor_data[:,:,:3]
        known=donor_data[:,:,3]>200
        _,nearest=cv2.distanceTransformWithLabels((~known).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        donor_rgb=donor_rgb[known][nearest-1]
        covered=(mask>0)&(bodyalpha>128)
        pixels[:,:,:3][covered]=donor_rgb[covered]
    else:pixels[:,:,3]=np.where(mask>0,0,original_alpha)
    body=Image.fromarray(pixels)
    bbox=source.getchannel('A').getbbox()
    def norm(im):
        im=im.crop(bbox)
        contained=p.ImageOps.contain(im,(560,403),Image.Resampling.LANCZOS)
        result=Image.new('RGBA',(640,480));result.alpha_composite(contained,((640-contained.width)//2,450-contained.height));return result
    body=norm(body);parts=[norm(part) for part in parts];frames=[]
    for k in range(36):
        t=math.tau*k/36;canvas=p.sway_tail(p.breathe(body,k,36),k,period=36,profile=3 if n==3 else None)
        for j,part in enumerate(parts):
            dx=1.8*math.sin(t+j*.9);dy=3.2*math.sin(t+j*1.3)
            layer=part.transform(part.size,Image.Transform.AFFINE,(1,0,-dx,0,1,-dy),Image.Resampling.BICUBIC)
            canvas.alpha_composite(layer)
        frames.append(canvas)
    return frames


def music():
    import cv2
    # One continuous deformation field: notes ripple, ears sway and the tail
    # counter-swings, with no rectangular or polygon cut-and-paste joints.
    im=Image.open(p.ASSETS/'hd'/'17.png').convert('RGBA').resize((640,480),Image.Resampling.LANCZOS)
    yy,xx=np.mgrid[:480,:640];frames=[]
    for k in range(36):
        t=math.tau*k/36
        upper=np.clip((370-yy)/250,0,1)**1.5
        dx=2*math.sin(t)*upper
        tail=p.small_tail_influence(17,im.size)
        dx-=5*math.sin(t)*tail
        notes=np.clip((185-yy)/50,0,1)
        dy=1.6*np.sin(t+xx*.035)*notes
        frames.append(p.remap_rgba(im,dx,dy))
    return frames


if __name__=='__main__':
    idle=p.neutral()
    for n in (3,20,17):
        p.restore(p.ITEMS[n-1])
        frames=music() if n==17 else floating(n)
        # Floating layers already have their own tail and breathing rig.
        p.encode(frames,p.ASSETS/'loops'/f'{n:02}.gif')
        item=p.ITEMS[n-1];p.transitions(idle,Image.open(p.ASSETS/'hd'/f'{n:02}.png').convert('RGBA'),item,frames)
        print('effect layers',n,flush=True)
