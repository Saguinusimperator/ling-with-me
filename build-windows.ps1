param(
    [string]$IndexUrl = 'https://pypi.tuna.tsinghua.edu.cn/simple',
    [switch]$SkipPackage
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

    & $python tools/build_windows.py --noconfirm --clean --onedir --windowed `
        --name Ling `
        --add-data 'pet/ling/spritesheet.webp;pet/ling' `
        --add-data 'pet/ling-heart/spritesheet.webp;pet/ling-heart' `
        --add-data 'pet/ling/perch.png;pet/ling' `
        --add-data 'pet/ling-heart/perch.png;pet/ling-heart' `
        --add-data 'pet/ling/hang.png;pet/ling' `
        --add-data 'pet/ling-heart/hang.png;pet/ling-heart' `
        --add-binary '.venv/Lib/site-packages/PySide6/plugins/platforms/qwindows.dll;PySide6/plugins/platforms' `
        ling_app.py
    if ($LASTEXITCODE -ne 0) { throw 'Could not build Ling.' }

    Write-Host 'Ling is ready at dist\Ling\Ling.exe'
    if (-not $SkipPackage) {
        Compress-Archive -LiteralPath 'dist\Ling', 'README.md', 'LICENSE-CODE.md', 'LICENSE-ART.md', 'LICENSE-SCRIPTS', 'THIRD-PARTY-NOTICES.md', 'MICROSOFT-TERMS.md', 'licenses' `
            -DestinationPath 'Ling-Windows.zip' -CompressionLevel Optimal -Force
        Write-Host 'Development package is ready at Ling-Windows.zip; verify CRT files before distribution.'
    }
} finally {
    Pop-Location
}
