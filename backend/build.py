from pathlib import Path
import PyInstaller.__main__

ROOT = Path(__file__).parent
PyInstaller.__main__.run([
    str(ROOT / "app" / "main.py"),
    "--name=python-backend",
    "--onefile",
    "--clean",
    "--noconfirm",
    "--paths", str(ROOT),
    "--collect-all", "uvicorn",
    "--collect-all", "fastapi",
    "--distpath", str(ROOT / "dist"),
    "--workpath", str(ROOT / "build"),
])
print(f"Build complete: {ROOT / 'dist' / 'python-backend'}")
