$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'pet\ling'
$sourceJson = Join-Path $source 'pet.json'
$sourceSheet = Join-Path $source 'spritesheet.webp'
if (-not (Test-Path -LiteralPath $sourceJson -PathType Leaf) -or
    -not (Test-Path -LiteralPath $sourceSheet -PathType Leaf)) {
    throw 'Ling pet files are missing. Download the complete repository and run this script from it.'
}

$pet = Get-Content -LiteralPath $sourceJson -Raw | ConvertFrom-Json
if ($pet.id -ne 'ling' -or $pet.spritesheetPath -ne 'spritesheet.webp') {
    throw 'pet/ling/pet.json does not describe the expected Ling package.'
}

$codexHome = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
} else {
    $env:CODEX_HOME
}
$petsDir = Join-Path $codexHome 'pets'
$destination = Join-Path $petsDir 'ling'

if (Test-Path -LiteralPath $destination) {
    if (-not (Test-Path -LiteralPath $destination -PathType Container)) {
        throw "Destination exists and is not a directory: $destination"
    }
    $existing = @(Get-ChildItem -LiteralPath $destination -Force)
    $names = @($existing | ForEach-Object { $_.Name } | Sort-Object)
    $expected = @('pet.json', 'spritesheet.webp')
    $sameNames = ($names.Count -eq $expected.Count) -and
                 (($names -join '|') -eq ($expected -join '|'))
    $sameFiles = $sameNames -and
                 (($existing | Where-Object { $_.Name -eq 'pet.json' }).PSIsContainer -eq $false) -and
                 (($existing | Where-Object { $_.Name -eq 'spritesheet.webp' }).PSIsContainer -eq $false) -and
                 ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceJson).Hash -eq
                  (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $destination 'pet.json')).Hash) -and
                 ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceSheet).Hash -eq
                  (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $destination 'spritesheet.webp')).Hash)
    if (-not $sameFiles) {
        throw "A different Ling pet already exists at $destination. Back it up or remove it manually before installing."
    }
    Write-Host "Ling is already installed at $destination"
    exit 0
}

New-Item -ItemType Directory -Path $petsDir -Force | Out-Null
$stage = Join-Path $petsDir ('.ling-install-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    Copy-Item -LiteralPath $sourceJson -Destination (Join-Path $stage 'pet.json')
    Copy-Item -LiteralPath $sourceSheet -Destination (Join-Path $stage 'spritesheet.webp')
    Move-Item -LiteralPath $stage -Destination $destination
} finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}

Write-Host "Ling installed at $destination"
Write-Host 'Open Settings > Pets > Refresh, select Ling, then enter /pet to show it.'
