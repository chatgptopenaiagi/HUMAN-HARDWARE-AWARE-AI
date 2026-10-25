param([switch]$SkipExecutable)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$previousCache = $env:PYINSTALLER_CONFIG_DIR
$env:PYINSTALLER_CONFIG_DIR = Join-Path $repoRoot '.preview-work/pyinstaller-cache'
Push-Location -LiteralPath $repoRoot
try {
    $previewVersion = python -c 'from awareness_kernel import __version__; print(__version__)'
    $artifactDirectory = Join-Path $repoRoot "dist/$previewVersion"
    python -m build --no-isolation --outdir $artifactDirectory
    if ($LASTEXITCODE) { throw 'Python distribution build failed' }
    $isolatedPython = Join-Path $repoRoot '.preview-work/venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $isolatedPython)) {
        python -m venv .preview-work/venv
        if ($LASTEXITCODE) { throw 'Isolated environment creation failed' }
    }
    $wheelPath = Join-Path $artifactDirectory "human_hardware_awareness_kernel-$previewVersion-py3-none-any.whl"
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
        & $isolatedPython -m PyInstaller --onefile --console --clean --noconfirm --name AwarenessKernel --paths $repoRoot --workpath ".preview-work/pyinstaller-$previewVersion" --specpath .preview-work --distpath $artifactDirectory @excludeArguments packaging/preview_entry.py
        if ($LASTEXITCODE) { throw 'EXE build failed' }
        python packaging/verify_genesis_1_3.py --python $isolatedPython --exe "$artifactDirectory/AwarenessKernel.exe" --results genesis-1.3/evidence/artifact-acceptance.json
    } else {
        python packaging/verify_genesis_1_3.py --python $isolatedPython --results genesis-1.3/evidence/artifact-acceptance.json
    }
    if ($LASTEXITCODE) { throw 'Artifact acceptance failed' }
} finally {
    $env:PYINSTALLER_CONFIG_DIR = $previousCache
    Pop-Location
}
