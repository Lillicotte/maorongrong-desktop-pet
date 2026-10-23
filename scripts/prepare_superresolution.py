"""Offline pixel-preserving SR preparation; no diffusion or character redraw."""
from pathlib import Path
import sys,json,hashlib,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'artifacts'/'sr-runtime'))
import cv2,numpy as np
from PIL import Image

def upsample_alpha(alpha,size):
    value=cv2.resize(alpha.astype('float32')/255,size,interpolation=cv2.INTER_CUBIC)
    return np.uint8(np.clip(value,0,1)*255+.5)

def main():
    sr=cv2.dnn_superres.DnnSuperResImpl_create()
    os.chdir(ROOT/'artifacts'/'models')
    sr.readModel('EDSR_x4.pb');sr.setModel('edsr',4)
    folder=ROOT/'assets'/'restored';folder.mkdir(exist_ok=True)
    for n in (2,3,17):
        source=ROOT/'assets'/'originals'/f'{n:02}.jpg'
        im=Image.open(source).convert('RGBA');raw=np.array(im)
        known=raw[:,:,3]>0
        _,labels=cv2.distanceTransformWithLabels((~known).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        rgb=raw[:,:,:3].copy();rgb[~known]=rgb[known][labels[~known]-1]
        restored=sr.upsample(rgb[:,:,::-1].copy())[:,:,::-1].astype('float32')
        baseline=cv2.resize(rgb,(im.width*4,im.height*4),interpolation=cv2.INTER_CUBIC).astype('float32')
        detail=restored-baseline
        detail-=cv2.GaussianBlur(detail,(0,0),5)
        out=baseline+np.clip(detail,-32,32)
        # Back projection keeps the original per-pixel palette and low-frequency shapes.
        for _ in range(2):
            small=cv2.resize(out,im.size,interpolation=cv2.INTER_AREA)
            out+=cv2.resize(rgb.astype('float32')-small,(im.width*4,im.height*4),interpolation=cv2.INTER_CUBIC)
        alpha=upsample_alpha(raw[:,:,3],(im.width*4,im.height*4))
        pixels=np.dstack([np.uint8(np.clip(out,0,255)+.5),alpha])
        Image.fromarray(pixels).save(folder/f'{n:02}-sr.png')
        print('SR ready',n,flush=True)
    (folder/'provenance.json').write_text(json.dumps({'algorithm':'EDSR x4, pixel back projection, original alpha contour','documentation':'https://docs.opencv.org/4.11.0/d5/d29/tutorial_dnn_superres_upscale_image_single.html','weights':'https://github.com/Saafke/EDSR_Tensorflow','model_sha256':hashlib.sha256((ROOT/'artifacts'/'models'/'EDSR_x4.pb').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
if __name__=='__main__':main()
