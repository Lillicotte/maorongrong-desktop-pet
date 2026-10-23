import os, sys, subprocess, shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir',
    '--name','猫溶溶','--add-data','assets;assets',
    '--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtWebEngineWidgets',
    '--exclude-module','PySide6.QtQml','--exclude-module','PySide6.QtQuick','app.py'],check=True)
# PyInstaller can pick up Poppler's incompatible ICU from PATH. Qt needs
# Windows' own ICU with unversioned exports. Leave those system DLLs to Windows.
for filename in ('icuuc.dll','icudt78.dll'):
    (root/'dist'/'猫溶溶'/'_internal'/filename).unlink(missing_ok=True)
shutil.copy2(root/'使用说明.md',root/'dist'/'猫溶溶'/'使用说明.md')
shutil.copy2(root/'行为规则.md',root/'dist'/'猫溶溶'/'行为规则.md')
# Playback uses WebP masters; GIF copies of internal clips and WebP copies of
# the shareable GIF exports are redundant in the portable distribution.
asset_root=(root/'dist'/'猫溶溶'/'_internal'/'assets').resolve()
for folder,suffix in [('loops','*.gif'),('transitions','*.gif'),('idles','*.gif'),('exits','*.gif'),('gif','*.webp')]:
    for file in (asset_root/folder).glob(suffix):
        if not file.resolve().is_relative_to(asset_root):raise RuntimeError('Unexpected asset path')
        file.unlink()
