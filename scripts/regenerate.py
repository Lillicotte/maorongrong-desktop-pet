import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for script in ('process_assets.py','build_idles.py','build_special_effects.py'):
    subprocess.run([sys.executable,str(root/'scripts'/script)],cwd=root,check=True)
