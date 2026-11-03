param(
    [string]$IndexUrl = 'https://pypi.tuna.tsinghua.edu.cn/simple'
)

$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This build script requires Windows.'
}

Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the build environment.' }
    }

    & $python -m pip install --disable-pip-version-check --index-url $IndexUrl -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }

    & $python -m PyInstaller --noconfirm --clean --onedir --windowed `
        --name Ling `
        --add-data 'pet/ling/spritesheet.webp;pet/ling' `
        --add-binary '.venv/Lib/site-packages/PySide6/plugins/platforms/qwindows.dll;PySide6/plugins/platforms' `
        ling_app.py
    if ($LASTEXITCODE -ne 0) { throw 'Could not build Ling.' }

    Write-Host 'Ling is ready at dist\Ling\Ling.exe'
} finally {
    Pop-Location
}
