[CmdletBinding()]
param(
    [string]$DestinationRoot = (Join-Path $HOME "ObsidianVault\HermesAgent")
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

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "ตรวจหลังติดตั้งไม่ผ่าน: ไม่พบ $Label ที่ $Path"
    }
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
