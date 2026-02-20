# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Ignition Toolbox Backend.

This bundles the FastAPI backend into a standalone executable
that can be distributed with the Electron app.

Build command:
    pyinstaller backend.spec --clean

Output:
    dist/backend/backend.exe (Windows)
    dist/backend/backend (Linux/Mac)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

# Get the backend directory
backend_dir = Path(SPECPATH)

# Find Playwright driver location
def get_playwright_driver():
    """Get Playwright driver binaries to include"""
    try:
        import playwright
        playwright_path = Path(playwright.__file__).parent
        driver_path = playwright_path / "driver"
        if driver_path.exists():
            return [(str(driver_path), "playwright/driver")]
    except ImportError:
        pass
    return []

# Collect all submodules for packages with dynamic imports
hidden_imports = [
    # FastAPI and dependencies
    *collect_submodules('fastapi'),
    *collect_submodules('starlette'),
    *collect_submodules('uvicorn'),
    *collect_submodules('pydantic'),
    *collect_submodules('pydantic_settings'),

    # SQLAlchemy
    *collect_submodules('sqlalchemy'),

    # Our application
    *collect_submodules('ignition_toolkit'),

    # Additional hidden imports
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'httptools',
    'websockets',
    'watchfiles',
    'aiosqlite',
    'apscheduler',
    'apscheduler.schedulers.asyncio',
    'apscheduler.triggers.cron',
    'apscheduler.triggers.interval',
    'apscheduler.jobstores.memory',
    'cryptography',
    'cryptography.fernet',
    'multipart',
    'python_multipart',
    'email_validator',
    'yaml',
    'psutil',
    # Playwright
    'playwright',
    'playwright.async_api',
    'playwright.sync_api',
    'playwright._impl',
    'playwright._impl._driver',
]

# Platform-specific imports
if sys.platform != 'win32':
    hidden_imports.append('uvloop')

# Collect data files
datas = [
    # Include playbooks directory
    (str(backend_dir / 'playbooks'), 'playbooks'),
    # Include CloudDesigner Docker files
    (str(backend_dir / 'ignition_toolkit' / 'clouddesigner' / 'docker_files'), 'clouddesigner/docker_files'),
    # Include StackBuilder catalog and integration data
    (str(backend_dir / 'ignition_toolkit' / 'stackbuilder' / 'data'), 'stackbuilder/data'),
]

# Add Playwright driver (required for browser installation command)
datas += get_playwright_driver()

# Add any package data files
datas += collect_data_files('pydantic')
datas += collect_data_files('starlette')
datas += collect_data_files('fastapi')
datas += collect_data_files('playwright')

a = Analysis(
    [str(backend_dir / 'run_backend.py')],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        # NOTE: PIL/Pillow is REQUIRED for visual testing (screenshot comparison)
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'cv2',
        'torch',
        'tensorflow',
        'pytest',
        'sphinx',
        'IPython',
        'notebook',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for logging output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
