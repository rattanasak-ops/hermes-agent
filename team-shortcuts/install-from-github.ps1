[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ArchiveUrl = if ($env:HERMES_SHORTCUT_ARCHIVE_URL) {
    $env:HERMES_SHORTCUT_ARCHIVE_URL
}
else {
    "https://github.com/rattanasak-ops/hermes-agent/archive/refs/heads/main.zip"
}
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("hermes-shortcuts-" + [guid]::NewGuid())
$ArchivePath = Join-Path $TempRoot "hermes-agent.zip"
$ExtractRoot = Join-Path $TempRoot "source"

try {
    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Write-Host "โหลดชุดคำสั่งลัดของทีมจาก GitHub"
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ArchivePath -UseBasicParsing
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ExtractRoot -Force

    $Installer = Get-ChildItem -Path $ExtractRoot -Filter "install-shortcuts.ps1" -File -Recurse |
        Where-Object { $_.Directory.Name -eq "team-shortcuts" } |
        Select-Object -First 1
    if ($null -eq $Installer) {
        throw "โหลดชุดติดตั้งแล้ว แต่ไม่พบ team-shortcuts/install-shortcuts.ps1"
    }

    & $Installer.FullName
}
finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
