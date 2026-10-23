import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
asset_root=(root/'dist'/'猫溶溶'/'_internal'/'assets').resolve()
for folder,suffix in [('loops','*.gif'),('transitions','*.gif'),('idles','*.gif'),('exits','*.gif'),('gif','*.webp')]:
    for file in (asset_root/folder).glob(suffix):
        if not file.resolve().is_relative_to(asset_root):raise RuntimeError('Unexpected asset path')
        file.unlink()
with zipfile.ZipFile(root/'猫溶溶-Windows便携版.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in (root/'dist'/'猫溶溶').rglob('*'):
        if file.is_file():z.write(file,file.relative_to(root/'dist'))
with zipfile.ZipFile(root/'猫溶溶-PNG与GIF.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for folder in ('originals','references','hd','gif','idles','exits'):
        for file in (root/'assets'/folder).glob('*'):
            if file.is_file() and file.suffix.lower() in ('.png','.gif','.jpg'):z.write(file,file.relative_to(root))
    z.write(root/'assets'/'manifest.json','assets/manifest.json')
    z.write(root/'使用说明.md','使用说明.md')
    z.write(root/'行为规则.md','行为规则.md')
for name in ('猫溶溶-Windows便携版.zip','猫溶溶-PNG与GIF.zip'):
    path=root/name
    with zipfile.ZipFile(path) as z:print(name,round(path.stat().st_size/1048576,1),'MB',len(z.infolist()),'files',flush=True)
