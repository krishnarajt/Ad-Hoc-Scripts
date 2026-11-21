<#
.SYNOPSIS
    Finds and removes all .venv and node_modules folders under a root folder.

.DESCRIPTION
    Prompts for a root folder, scans it recursively, lists every .venv and
    node_modules folder found (with sizes), then asks what to do: delete all,
    review one by one, or cancel. Nothing is deleted without confirmation.
    Reports the total disk space recovered at the end.
#>

$TargetNames = @('.venv', 'node_modules')

# ---------- Helpers ----------
function Format-Size {
    param([long]$Bytes)
    if     ($Bytes -ge 1GB) { '{0:N2} GB' -f ($Bytes / 1GB) }
    elseif ($Bytes -ge 1MB) { '{0:N2} MB' -f ($Bytes / 1MB) }
    elseif ($Bytes -ge 1KB) { '{0:N2} KB' -f ($Bytes / 1KB) }
    else                    { "$Bytes B" }
}

function Get-FolderSize {
    param([string]$Path)
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { 0 } else { [long]$sum }
}

# ---------- Ask for the root folder ----------
$rootInput = Read-Host "Enter the root folder to clean (leave blank for current folder)"
$rootInput = $rootInput.Trim().Trim('"').Trim("'")
if ([string]::IsNullOrWhiteSpace($rootInput)) { $rootInput = (Get-Location).Path }

if (-not (Test-Path -LiteralPath $rootInput -PathType Container)) {
    Write-Host "Folder not found: $rootInput" -ForegroundColor Red
    exit 1
}
$Root = (Resolve-Path -LiteralPath $rootInput).Path

# Safety: refuse to run on a drive root (e.g. C:\)
if ($Root -eq [System.IO.Path]::GetPathRoot($Root)) {
    Write-Host "Refusing to scan a drive root ($Root). Pick a specific folder." -ForegroundColor Red
    exit 1
}

# ---------- Scan (does not descend into matches or symlinks/junctions) ----------
function Find-Targets {
    param([string]$StartPath)

    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($StartPath)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        try {
            $dirs = Get-ChildItem -LiteralPath $current -Directory -Force -ErrorAction Stop
        } catch {
            continue
        }
        foreach ($d in $dirs) {
            if ($d.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { continue }
            if ($TargetNames -contains $d.Name) {
                $d
            } else {
                $stack.Push($d.FullName)
            }
        }
    }
}

Write-Host "`nScanning $Root ..." -ForegroundColor Cyan
$dirsFound = @(Find-Targets -StartPath $Root)

if ($dirsFound.Count -eq 0) {
    Write-Host "No .venv or node_modules folders found." -ForegroundColor Green
    exit 0
}

# ---------- Measure sizes ----------
Write-Host "Measuring sizes (this can take a moment) ..." -ForegroundColor Cyan
$found = foreach ($d in $dirsFound) {
    [PSCustomObject]@{
        FullName = $d.FullName
        Size     = Get-FolderSize -Path $d.FullName
    }
}

$totalSize = ($found | Measure-Object -Property Size -Sum).Sum

Write-Host "`nFound $($found.Count) folder(s), $(Format-Size $totalSize) total:" -ForegroundColor Yellow
$found | ForEach-Object {
    Write-Host ("  {0,10}  {1}" -f (Format-Size $_.Size), $_.FullName)
}

# ---------- Removal helper ----------
function Remove-Target {
    param([string]$Path)
    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        return $true
    } catch {
        # Fallback for very long paths that Remove-Item can choke on
        cmd /c "rmdir /s /q `"$Path`"" 2>$null
        return -not (Test-Path -LiteralPath $Path)
    }
}

# ---------- Ask what to do ----------
$choices = @(
    [System.Management.Automation.Host.ChoiceDescription]::new('&Delete all',        'Delete every folder listed above'),
    [System.Management.Automation.Host.ChoiceDescription]::new('&Review one by one', 'Confirm each folder individually'),
    [System.Management.Automation.Host.ChoiceDescription]::new('&Cancel',            'Do nothing')
)
$answer = $Host.UI.PromptForChoice("`nWhat would you like to do?", "Root: $Root", $choices, 2)

$deleted   = 0
$failed    = 0
$recovered = [long]0

switch ($answer) {
    0 {
        foreach ($f in $found) {
            Write-Host "Deleting $($f.FullName) ..." -NoNewline
            if (Remove-Target -Path $f.FullName) {
                Write-Host " done ($(Format-Size $f.Size))" -ForegroundColor Green
                $deleted++
                $recovered += $f.Size
            } else {
                Write-Host " FAILED" -ForegroundColor Red
                $failed++
            }
        }
    }
    1 {
        $yn = @(
            [System.Management.Automation.Host.ChoiceDescription]::new('&Yes',  'Delete this folder'),
            [System.Management.Automation.Host.ChoiceDescription]::new('&No',   'Skip this folder'),
            [System.Management.Automation.Host.ChoiceDescription]::new('&Quit', 'Stop reviewing')
        )
        foreach ($f in $found) {
            $r = $Host.UI.PromptForChoice("", "Delete $($f.FullName) ($(Format-Size $f.Size))?", $yn, 1)
            if ($r -eq 2) { break }
            if ($r -eq 0) {
                if (Remove-Target -Path $f.FullName) {
                    Write-Host "  deleted" -ForegroundColor Green
                    $deleted++
                    $recovered += $f.Size
                } else {
                    Write-Host "  FAILED" -ForegroundColor Red
                    $failed++
                }
            }
        }
    }
    default {
        Write-Host "Cancelled. Nothing was deleted." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`nDone. Deleted: $deleted  Failed: $failed" -ForegroundColor Cyan
Write-Host "Space recovered: $(Format-Size $recovered)" -ForegroundColor Green