#requires -Version 5.1
<#
Installs all three supplied Skill folders. No network, no elevation,
no profile/config edits, and no replacement of existing target paths.
Usage: powershell -NoProfile -File .\Install-GAS-Skills.ps1
Preview: powershell -NoProfile -File .\Install-GAS-Skills.ps1 -WhatIf
Validation scope and Windows smoke-test results are recorded in VALIDATION.md.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string] $Destination = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$skillNames = @('gas-centralized-development', 'gas-decentralized-development', 'gas-combined-development')
$sourceRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$manifestPath = [System.IO.Path]::Combine($sourceRoot, 'manifest.sha256.json')

function Assert-NoReparsePoint {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $attributes = [System.IO.File]::GetAttributes($LiteralPath)
    if (($attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a symbolic-link or reparse-point path: $LiteralPath"
    }
}

function Get-VerifiedInventory {
    param(
        [Parameter(Mandatory = $true)][string] $Root,
        [Parameter(Mandatory = $true)] $Manifest,
        [Parameter(Mandatory = $true)][string[]] $Names
    )
    $rootPrefix = $Root.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
    foreach ($name in $Names) {
        $skillRoot = [System.IO.Path]::Combine($Root, $name)
        if (-not [System.IO.Directory]::Exists($skillRoot)) {
            throw "Missing Skill folder: $skillRoot"
        }
        Assert-NoReparsePoint -LiteralPath $skillRoot
        $items = @(Get-ChildItem -LiteralPath $skillRoot -Recurse -Force)
        foreach ($item in $items) {
            Assert-NoReparsePoint -LiteralPath $item.FullName
        }
        $files = @($items | Where-Object { -not $_.PSIsContainer })
        $expected = @($Manifest.files.PSObject.Properties | Where-Object {
            $_.Name.StartsWith($name + '/', [System.StringComparison]::Ordinal)
        })
        if (($expected.Count -eq 0) -or ($expected.Count -ne $files.Count)) {
            throw "Manifest file-count mismatch for $name"
        }
        $seen = New-Object 'System.Collections.Generic.HashSet[string]'
        foreach ($file in $files) {
            if (-not $file.FullName.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Source path is outside the package: $($file.FullName)"
            }
            $relative = $file.FullName.Substring($rootPrefix.Length).Replace('\', '/')
            $property = $Manifest.files.PSObject.Properties[$relative]
            if ($null -eq $property) {
                throw "File is not declared in the manifest: $relative"
            }
            $actualHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualHash -ne [string] $property.Value) {
                throw "SHA-256 mismatch: $relative"
            }
            [void] $seen.Add($relative)
            [PSCustomObject] @{
                Relative = $relative
                Source = $file.FullName
                SHA256 = $actualHash
            }
        }
        foreach ($entry in $expected) {
            if (-not $seen.Contains($entry.Name)) {
                throw "Manifest entry has no matching source file: $($entry.Name)"
            }
        }
    }
}

if (-not [System.IO.File]::Exists($manifestPath)) {
    throw 'Missing manifest.sha256.json. Extract the complete package before installation.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (($manifest.algorithm -ne 'sha256') -or ($manifest.version -ne 1)) {
    throw 'Unsupported manifest format.'
}
$inventory = @(Get-VerifiedInventory -Root $sourceRoot -Manifest $manifest -Names $skillNames)

if (-not [System.IO.Path]::IsPathRooted($Destination)) {
    throw 'Destination must be an absolute filesystem path.'
}
$destinationFull = [System.IO.Path]::GetFullPath($Destination)
$driveRoot = [System.IO.Path]::GetPathRoot($destinationFull)
if (-not (Test-Path -LiteralPath $driveRoot -PathType Container)) {
    throw "Destination drive/share is not available: $driveRoot"
}
$sourcePrefix = $sourceRoot.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
if (($destinationFull -eq $sourceRoot) -or $destinationFull.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose a destination outside the extracted source package. No files were installed.'
}
if ((Test-Path -LiteralPath $destinationFull) -and (-not [System.IO.Directory]::Exists($destinationFull))) {
    throw "Destination is not a directory: $destinationFull"
}

# Refuse redirected destination ancestors instead of following junctions or links.
$cursor = $destinationFull
while ($cursor) {
    if (Test-Path -LiteralPath $cursor) {
        Assert-NoReparsePoint -LiteralPath $cursor
    }
    $parent = [System.IO.Directory]::GetParent($cursor)
    if ($null -eq $parent) { break }
    $cursor = $parent.FullName
}

# Check ALL folders before any directory creation or copying.
foreach ($name in $skillNames) {
    $target = [System.IO.Path]::Combine($destinationFull, $name)
    if (Test-Path -LiteralPath $target) {
        throw "Refusing to overwrite existing target: $target. No Skill has been installed by this run."
    }
}
if (-not $PSCmdlet.ShouldProcess($destinationFull, 'Install the three GAS Skill folders without overwriting existing paths')) {
    return
}

$stage = $null
$installed = New-Object 'System.Collections.Generic.List[string]'
try {
    [void] [System.IO.Directory]::CreateDirectory($destinationFull)
    $stage = [System.IO.Path]::Combine($destinationFull, '.gas-skill-install-' + [guid]::NewGuid().ToString('N'))
    [void] [System.IO.Directory]::CreateDirectory($stage)
    foreach ($entry in $inventory) {
        $relativeNative = $entry.Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $stagedFile = [System.IO.Path]::Combine($stage, $relativeNative)
        [void] [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($stagedFile))
        [System.IO.File]::Copy($entry.Source, $stagedFile, $false)
    }
    # Verify the staged copies before promoting any folder.
    $stagedInventory = @(Get-VerifiedInventory -Root $stage -Manifest $manifest -Names $skillNames)
    if ($stagedInventory.Count -ne $inventory.Count) {
        throw 'Staged inventory does not match the source.'
    }
    foreach ($name in $skillNames) {
        $from = [System.IO.Path]::Combine($stage, $name)
        $to = [System.IO.Path]::Combine($destinationFull, $name)
        # Directory.Move rejects an existing destination, including a late collision.
        [System.IO.Directory]::Move($from, $to)
        [void] $installed.Add($to)
    }
    Write-Host 'Installed Skill folders:'
    foreach ($path in $installed) { Write-Host ('  ' + $path) }
    Write-Host 'No IDE settings or Skill auto-discovery configuration were changed.'
}
catch {
    $partial = if ($installed.Count -gt 0) {
        'Already installed in this run: ' + ($installed -join '; ') + '. These folders were retained.'
    } else {
        'No Skill folder was installed.'
    }
    throw ('Installation failed. ' + $partial + ' The installer does not overwrite existing Skill folders. Details: ' + $_.Exception.Message)
}
finally {
    if (($null -ne $stage) -and [System.IO.Directory]::Exists($stage)) {
        try {
            # This is only the unique staging directory created by this invocation.
            Remove-Item -LiteralPath $stage -Recurse -Force
        }
        catch {
            Write-Warning ('Temporary staging directory could not be removed: ' + $stage)
        }
    }
}
