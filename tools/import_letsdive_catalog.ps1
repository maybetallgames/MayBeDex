param(
    [Parameter(Mandatory = $true)]
    [string]$LetsDivePath
)

$ErrorActionPreference = 'Stop'

$source = Join-Path $LetsDivePath 'PrefabPreviews\Synty'
$destination = Join-Path $PSScriptRoot '..\catalog-source'

if (-not (Test-Path $source)) {
    throw "Could not find LetsDive Synty catalog export at: $source"
}

New-Item -ItemType Directory -Force -Path $destination | Out-Null

$required = @('_lookup.tsv')
$optional = @('_catalog.json')

foreach ($name in $required) {
    $sourceFile = Join-Path $source $name
    if (-not (Test-Path $sourceFile)) {
        throw "Required catalog file is missing: $sourceFile. Run the LetsDive prefab preview/catalog generator first."
    }

    Copy-Item -Force $sourceFile (Join-Path $destination $name)
    Write-Host "Copied $name"
}

foreach ($name in $optional) {
    $sourceFile = Join-Path $source $name
    if (Test-Path $sourceFile) {
        Copy-Item -Force $sourceFile (Join-Path $destination $name)
        Write-Host "Copied $name"
    }
}

Write-Host ''
Write-Host 'MayBeDex metadata import complete.'
Write-Host 'No Synty preview images or base64 image sidecars were copied.'
Write-Host 'Next: review git diff, commit, and push.'
