from pathlib import Path
import pefile
root=Path(__file__).resolve().parents[1]/'dist'/'猫溶溶'/'_internal'
files={p.name.lower():p for p in root.rglob('*') if p.suffix.lower() in ('.pyd','.dll')}
for name in ('qtcore.pyd','qt6core.dll','pyside6.abi3.dll','shiboken6.abi3.dll','icuuc.dll'):
    p=files[name];pe=pefile.PE(str(p))
    for dep in pe.DIRECTORY_ENTRY_IMPORT:
        key=dep.dll.decode().lower()
        dll=files.get(key)
        if not dll and not key.startswith('api-'):dll=Path('C:/Windows/System32')/key
        if not dll or not dll.exists():continue
        lib=pefile.PE(str(dll))
        exports={s.name for s in lib.DIRECTORY_ENTRY_EXPORT.symbols}
        missing=[s.name.decode() for s in dep.imports if s.name and s.name not in exports]
        if missing:print(name,'->',str(dll),missing)
