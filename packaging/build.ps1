param([switch]$SkipExecutable)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$previousCache = $env:PYINSTALLER_CONFIG_DIR
$env:PYINSTALLER_CONFIG_DIR = Join-Path $repoRoot '.preview-work/pyinstaller-cache'
Push-Location -LiteralPath $repoRoot
try {
    python -m build --no-isolation
    if ($LASTEXITCODE) { throw 'Python distribution build failed' }
    $isolatedPython = Join-Path $repoRoot '.preview-work/venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $isolatedPython)) {
        python -m venv .preview-work/venv
        if ($LASTEXITCODE) { throw 'Isolated environment creation failed' }
    }
    $wheelPath = Join-Path $repoRoot 'dist/human_hardware_awareness_kernel-0.1.2.dev1-py3-none-any.whl'
    & $isolatedPython -m pip install --no-index --no-deps --force-reinstall $wheelPath
    if ($LASTEXITCODE) { throw 'Wheel installation failed' }
    if (-not $SkipExecutable) {
        & $isolatedPython -c 'import PyInstaller' 2>$null
        if ($LASTEXITCODE) {
            & $isolatedPython -m pip install 'PyInstaller==6.22.3'
            if ($LASTEXITCODE) { throw 'Single EXE packager unavailable' }
        }
        # The evaluation CLI needs neither crypto/network nor optional archive/decimal/ctypes adapters.
        $excludedModules = @('ssl', '_ssl', '_hashlib', 'decimal', '_decimal', 'lzma', '_lzma', 'bz2', '_bz2', 'compression.zstd', '_zstd', 'ctypes', '_ctypes')
        $excludeArguments = @()
        foreach ($moduleName in $excludedModules) { $excludeArguments += @('--exclude-module', $moduleName) }
        & $isolatedPython -m PyInstaller --onefile --console --clean --noconfirm --name AwarenessKernel --paths $repoRoot --workpath .preview-work/pyinstaller --specpath .preview-work --distpath dist @excludeArguments packaging/preview_entry.py
        if ($LASTEXITCODE) { throw 'EXE build failed' }
        python packaging/verify_artifacts.py --python $isolatedPython --exe dist/AwarenessKernel.exe --results genesis-1.2/evidence/artifact-acceptance.json
    } else {
        python packaging/verify_artifacts.py --python $isolatedPython --results genesis-1.2/evidence/artifact-acceptance.json
    }
    if ($LASTEXITCODE) { throw 'Artifact acceptance failed' }
} finally {
    $env:PYINSTALLER_CONFIG_DIR = $previousCache
    Pop-Location
}
