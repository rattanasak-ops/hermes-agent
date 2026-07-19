[CmdletBinding()]
param(
    [string]$DestinationRoot = (Join-Path $HOME "ObsidianVault\HermesAgent"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $ScriptRoot "payload"
$VersionFile = Join-Path $ScriptRoot "VERSION"
$RegistrySource = Join-Path $PayloadRoot "ai-context\prompt-shortcut-registry.md"
$SkillSource = Join-Path $PayloadRoot "skills\prompt-shortcuts"
$AgentSkillSource = Join-Path $PayloadRoot "skills\agent-center"
$AgentPluginSource = Join-Path $ScriptRoot "..\plugins\agent_center"
$RegistryDestination = Join-Path $DestinationRoot "ai-context\prompt-shortcut-registry.md"
$SkillDestination = Join-Path $DestinationRoot "skills\prompt-shortcuts"
$AgentSkillDestination = Join-Path $DestinationRoot "skills\agent-center"
$ReferencesDestination = Join-Path $SkillDestination "references"
$CodexPointer = Join-Path $HOME ".codex\skills\prompt-shortcuts"
$CodexAgentPointer = Join-Path $HOME ".codex\skills\agent-center"
$CursorPointer = Join-Path $HOME ".cursor\rules\hermes-prompt-shortcuts.mdc"
$InstalledVersion = Join-Path $DestinationRoot ".shortcut-version"

$HermesCommand = Get-Command hermes -ErrorAction SilentlyContinue
if ($null -eq $HermesCommand) {
    throw "ไม่พบคำสั่ง hermes — Use Agent ต้องมี Hermes Agent ก่อนติดตั้ง"
}
$HermesHome = if ($env:HERMES_HOME) {
    $env:HERMES_HOME
}
else {
    $dump = (& $HermesCommand.Source dump 2>$null | Select-String '^hermes_home:\s*(.+)$' | Select-Object -First 1)
    if ($null -ne $dump) {
        $reported = $dump.Matches[0].Groups[1].Value.Trim()
        if ($reported -eq "~") { $HOME }
        elseif ($reported.StartsWith("~\") -or $reported.StartsWith("~/")) {
            Join-Path $HOME $reported.Substring(2)
        }
        else { $reported }
    }
    else {
        Join-Path $HOME ".hermes"
    }
}
$AgentPluginDestination = Join-Path $HermesHome "plugins\agent-center"
$HermesAgentSkillDestination = Join-Path $HermesHome "skills\agent-center"

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "ตรวจหลังติดตั้งไม่ผ่าน: ไม่พบ $Label ที่ $Path"
    }
}

function Test-RealDirectory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return $false
    }
    $item = Get-Item -LiteralPath $Path -Force
    return (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0)
}

function Add-NewerFileConflict(
    [string]$Source,
    [string]$Destination,
    [string]$Label
) {
    if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        return
    }
    $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) {
        $sourceTime = (Get-Item -LiteralPath $Source).LastWriteTimeUtc
        $destinationTime = (Get-Item -LiteralPath $Destination).LastWriteTimeUtc
        if ($destinationTime -gt $sourceTime) {
            $script:NewerConflicts += $Label
        }
    }
}

function Add-NewerTreeConflicts(
    [string]$Source,
    [string]$Destination,
    [string]$Label
) {
    if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
        return
    }
    foreach ($sourceFile in Get-ChildItem -LiteralPath $Source -File -Recurse) {
        $relative = $sourceFile.FullName.Substring($Source.TrimEnd('\').Length).TrimStart('\')
        Add-NewerFileConflict `
            $sourceFile.FullName `
            (Join-Path $Destination $relative) `
            "$Label\$relative"
    }
    foreach ($destinationFile in Get-ChildItem -LiteralPath $Destination -File -Recurse) {
        $relative = $destinationFile.FullName.Substring($Destination.TrimEnd('\').Length).TrimStart('\')
        $isGenerated = $relative -match '(^|\\)__pycache__(\\|$)' -or
            $relative.EndsWith('.pyc') -or
            $relative.EndsWith('.pyo') -or
            $relative.EndsWith('.DS_Store')
        if (-not $isGenerated -and -not (Test-Path -LiteralPath (Join-Path $Source $relative))) {
            $script:NewerConflicts += "$Label\$relative (มีเฉพาะปลายทาง)"
        }
    }
}

function Copy-BackupDirectory([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Get-TableRowCount([string]$Path) {
    $count = 0
    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        if ($line.StartsWith('| `')) {
            $count++
        }
    }
    return $count
}

function Get-SkillMapRowCount([string]$Path) {
    $active = $false
    $count = 0
    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        if ($line -eq "## Shortcut Map") {
            $active = $true
            continue
        }
        if ($active -and $line.StartsWith("## ")) {
            break
        }
        if ($active -and $line.StartsWith('| `')) {
            $count++
        }
    }
    return $count
}

if (-not (Test-Path -LiteralPath $RegistrySource -PathType Leaf)) {
    throw "ไม่พบชุดติดตั้งที่ $RegistrySource"
}
if (-not (Test-Path -LiteralPath $SkillSource -PathType Container)) {
    throw "ไม่พบชุดคำสั่งลัดที่ $SkillSource"
}
if (-not (Test-Path -LiteralPath $AgentSkillSource -PathType Container)) {
    throw "ไม่พบ Agent Center skill ที่ $AgentSkillSource"
}
if (-not (Test-Path -LiteralPath $AgentPluginSource -PathType Container)) {
    throw "ไม่พบ Agent Center plugin ที่ $AgentPluginSource"
}
Assert-File $VersionFile "หมายเลขชุดติดตั้ง"

$script:NewerConflicts = @()
Add-NewerFileConflict $RegistrySource $RegistryDestination "ai-context\prompt-shortcut-registry.md"
Add-NewerTreeConflicts $SkillSource $SkillDestination "skills\prompt-shortcuts"
Add-NewerTreeConflicts $AgentSkillSource $AgentSkillDestination "skills\agent-center"
Add-NewerTreeConflicts $AgentSkillSource $HermesAgentSkillDestination "Hermes runtime skill\agent-center"
Add-NewerTreeConflicts $AgentPluginSource $AgentPluginDestination "Hermes runtime plugin\agent-center"
if (Test-RealDirectory $CodexPointer) {
    Add-NewerTreeConflicts $SkillSource $CodexPointer "Codex skill\prompt-shortcuts"
}
if (Test-RealDirectory $CodexAgentPointer) {
    Add-NewerTreeConflicts $AgentSkillSource $CodexAgentPointer "Codex skill\agent-center"
}
if ($script:NewerConflicts.Count -gt 0 -and -not $Force) {
    $details = $script:NewerConflicts | Sort-Object -Unique | ForEach-Object { " - $_" }
    throw "พบไฟล์ปลายทางใหม่กว่าชุดติดตั้ง จึงหยุดเพื่อไม่ให้ข้อมูลหาย:`n$($details -join "`n")`nตรวจไฟล์ก่อน หรือรันใหม่พร้อม -Force"
}

$backupSourcesExist = @(
    $RegistryDestination,
    $SkillDestination,
    $AgentSkillDestination,
    $HermesAgentSkillDestination,
    $AgentPluginDestination
) | Where-Object { Test-Path -LiteralPath $_ }
if (Test-RealDirectory $CodexPointer) { $backupSourcesExist += $CodexPointer }
if (Test-RealDirectory $CodexAgentPointer) { $backupSourcesExist += $CodexAgentPointer }
if ($backupSourcesExist.Count -gt 0) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupRoot = Join-Path $DestinationRoot ".backup-shortcuts-$stamp"
    $suffix = 1
    while (Test-Path -LiteralPath $backupRoot) {
        $backupRoot = Join-Path $DestinationRoot ".backup-shortcuts-$stamp-$suffix"
        $suffix++
    }
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    if (Test-Path -LiteralPath $RegistryDestination -PathType Leaf) {
        $registryBackup = Join-Path $backupRoot "ai-context\prompt-shortcut-registry.md"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $registryBackup) | Out-Null
        Copy-Item -LiteralPath $RegistryDestination -Destination $registryBackup -Force
    }
    Copy-BackupDirectory $SkillDestination (Join-Path $backupRoot "skills\prompt-shortcuts")
    Copy-BackupDirectory $AgentSkillDestination (Join-Path $backupRoot "skills\agent-center")
    Copy-BackupDirectory $HermesAgentSkillDestination (Join-Path $backupRoot "runtime-skills\agent-center")
    Copy-BackupDirectory $AgentPluginDestination (Join-Path $backupRoot "runtime-plugins\agent-center")
    if (Test-RealDirectory $CodexPointer) {
        Copy-BackupDirectory $CodexPointer (Join-Path $backupRoot "codex-skills\prompt-shortcuts")
    }
    if (Test-RealDirectory $CodexAgentPointer) {
        Copy-BackupDirectory $CodexAgentPointer (Join-Path $backupRoot "codex-skills\agent-center")
    }
    Get-ChildItem -LiteralPath $DestinationRoot -Directory -Filter ".backup-shortcuts-*" |
        Sort-Object Name -Descending |
        Select-Object -Skip 5 |
        Remove-Item -Recurse -Force
    Write-Step "สำรองของเดิมไว้ที่ $backupRoot"
}

Write-Step "[1/4] คัดชุดคำสั่งลัดไป $DestinationRoot"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $RegistryDestination) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SkillDestination) | Out-Null
Copy-Item -LiteralPath $RegistrySource -Destination $RegistryDestination -Force
if (Test-Path -LiteralPath $SkillDestination) {
    Remove-Item -LiteralPath $SkillDestination -Recurse -Force
}
Copy-Item -LiteralPath $SkillSource -Destination $SkillDestination -Recurse -Force
if (Test-Path -LiteralPath $AgentSkillDestination) {
    Remove-Item -LiteralPath $AgentSkillDestination -Recurse -Force
}
Copy-Item -LiteralPath $AgentSkillSource -Destination $AgentSkillDestination -Recurse -Force
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $HermesAgentSkillDestination) | Out-Null
if (Test-Path -LiteralPath $HermesAgentSkillDestination) {
    Remove-Item -LiteralPath $HermesAgentSkillDestination -Recurse -Force
}
Copy-Item -LiteralPath $AgentSkillSource -Destination $HermesAgentSkillDestination -Recurse -Force
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $AgentPluginDestination) | Out-Null
if (Test-Path -LiteralPath $AgentPluginDestination) {
    Remove-Item -LiteralPath $AgentPluginDestination -Recurse -Force
}
Copy-Item -LiteralPath $AgentPluginSource -Destination $AgentPluginDestination -Recurse -Force
Copy-Item -LiteralPath $VersionFile -Destination $InstalledVersion -Force
& $HermesCommand.Source plugins enable agent-center
if ($LASTEXITCODE -ne 0) {
    throw "คัด Agent Center แล้ว แต่เปิดใช้ผ่าน Hermes Agent ไม่สำเร็จ"
}
& $HermesCommand.Source config set plugins.entries.agent-center.llm.allow_provider_override true
if ($LASTEXITCODE -ne 0) {
    throw "เปิดสิทธิ์เลือกผู้ให้บริการสำหรับ Agent Center ไม่สำเร็จ"
}
& $HermesCommand.Source config set plugins.entries.agent-center.llm.allow_model_override true
if ($LASTEXITCODE -ne 0) {
    throw "เปิดสิทธิ์เลือกรุ่น AI สำหรับ Agent Center ไม่สำเร็จ"
}

Write-Step "[2/4] ทำจุดเชื่อมสำหรับ Codex App"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CodexPointer) | Out-Null
if (Test-Path -LiteralPath $CodexPointer) {
    $item = Get-Item -LiteralPath $CodexPointer -Force
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        Remove-Item -LiteralPath $CodexPointer -Force
    }
    else {
        Remove-Item -LiteralPath $CodexPointer -Recurse -Force
    }
}
New-Item -ItemType Junction -Path $CodexPointer -Target $SkillDestination | Out-Null
if (Test-Path -LiteralPath $CodexAgentPointer) {
    Remove-Item -LiteralPath $CodexAgentPointer -Recurse -Force
}
New-Item -ItemType Junction -Path $CodexAgentPointer -Target $AgentSkillDestination | Out-Null

Write-Step "[3/4] สร้างกฎชี้ตำแหน่งสำหรับ Cursor"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CursorPointer) | Out-Null
$cursorRule = @"
---
description: เปิดทะเบียน Prompt Shortcut ของ Hermes Agent ก่อนใช้คำสั่งลัด
alwaysApply: true
---

เมื่อผู้ใช้เรียก Prompt Shortcut ให้เปิดไฟล์ต่อไปนี้ก่อน และห้ามเดาจากความจำ:

- ทะเบียน: $RegistryDestination
- ชุดคำสั่งลัด: $SkillDestination\SKILL.md
- สัญญาการทำงาน: $ReferencesDestination\worktree-lifecycle-contract.md
"@
Set-Content -LiteralPath $CursorPointer -Value $cursorRule -Encoding UTF8

Write-Step "[4/4] ตรวจ Migrate 14/14 และสัญญาหลังติดตั้ง"
Assert-File $RegistryDestination "ทะเบียนคำสั่งลัด"
Assert-File (Join-Path $SkillDestination "SKILL.md") "ชุดคำสั่งลัด"
Assert-File (Join-Path $SkillDestination "Prompt Shortcuts.md") "สารบัญคำสั่งลัด"
Assert-File (Join-Path $AgentSkillDestination "SKILL.md") "Agent Center skill"
Assert-File (Join-Path $HermesAgentSkillDestination "SKILL.md") "Hermes Agent runtime skill"
Assert-File (Join-Path $AgentPluginDestination "plugin.yaml") "Agent Center plugin"
Assert-File (Join-Path $ReferencesDestination "use-migrate-phase-contract.md") "สัญญากลาง Migrate"
Assert-File $CursorPointer "กฎ Cursor"

$migrateCount = 0
foreach ($phase in 0..13) {
    $phaseFile = Join-Path $ReferencesDestination "use-migrate-$phase.md"
    Assert-File $phaseFile "Migrate ระยะ $phase"
    $migrateCount++
}
if ($migrateCount -ne 14) {
    throw "ตรวจหลังติดตั้งไม่ผ่าน: Migrate มี $migrateCount/14"
}

$registryCount = Get-TableRowCount $RegistryDestination
$skillCount = Get-SkillMapRowCount (Join-Path $SkillDestination "SKILL.md")
$indexCount = Get-TableRowCount (Join-Path $SkillDestination "Prompt Shortcuts.md")
if ($registryCount -le 0 -or $registryCount -ne $skillCount -or $registryCount -ne $indexCount) {
    throw "ตรวจสัญญาหลังติดตั้งไม่ผ่าน: ทะเบียน=$registryCount ชุดคำสั่งลัด=$skillCount สารบัญ=$indexCount"
}
if (-not (Test-Path -LiteralPath $CodexPointer -PathType Container)) {
    throw "ตรวจหลังติดตั้งไม่ผ่าน: Codex App มองไม่เห็น $CodexPointer"
}

Write-Host "RESULT: PASS"
Write-Host "Migrate $migrateCount/14 และสัญญากลางครบ · รายการคำสั่งลัด $registryCount/$registryCount"
Write-Warning "เครื่องมือ MW ใน scripts/mw ยังเป็น shell script ต้องเปิดตัวติดตั้งนี้ผ่าน WSL หรือ Git Bash หากต้องใช้ MW บน Windows; ตัวติดตั้ง PowerShell นี้ไม่ได้อ้างว่ารองรับ MW โดยตรง"
Write-Host "ปิดแล้วเปิด Cursor และ Codex App ใหม่ 1 รอบก่อนใช้งาน"
