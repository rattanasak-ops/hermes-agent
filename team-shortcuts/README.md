# ชุดติดตั้ง Prompt Shortcut สำหรับทีม

ชุดนี้ทำให้พนักงานใช้ Shortcut และ AI Relay ได้บน Notebook กับ VPS
ทั้งใน **Cursor, Claude Code และ Codex** เหมือนเครื่องเจ้าของระบบ

## ปัญหาที่ชุดนี้แก้

ไฟล์ตัวเชื่อมในแต่ละโปรเจกต์ชี้ไปที่อยู่เต็มของเครื่องเจ้าของระบบ
(`/Users/rattanasak/ObsidianVault/HermesAgent/...`) ซึ่งไม่มีบนเครื่องพนักงาน
พอ AI หาเนื้อ Shortcut ไม่เจอ จึงใช้ไม่ได้ ตัวติดตั้งนี้วางชุด Shortcut ลงเครื่องพนักงาน
แล้วต่อสายให้ทั้ง 3 โปรแกรมมองเห็น

## วิธีติดตั้งบน Mac

พนักงานไม่ต้องมี repo Hermes Agent ในเครื่อง คำสั่งต่อไปนี้ติดตั้งให้ Codex App:

```bash
curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.sh | bash
```

ถ้าต้องการให้ Cursor เห็น Shortcut ด้วย ให้เพิ่ม `--cursor`:

```bash
curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.sh | bash -s -- --cursor
```

คำสั่ง Mac ติดตั้งทั้ง Shortcut, AI Relay และเพิ่ม `~/.local/bin` ให้ zsh/bash แล้ว

## วิธีติดตั้งบน Windows

เปิด PowerShell แบบปกติ ไม่ต้องเปิดด้วยสิทธิ์ผู้ดูแล แล้วรันคำสั่งนี้ คำสั่งเดียวติดตั้ง Shortcut ให้ทั้ง Cursor และ Codex App:

```powershell
irm https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.ps1 | iex
```

ตัวติดตั้ง Windows ชุดนี้ยืนยันเฉพาะการวาง Shortcut และจุดเชื่อมสำหรับ Cursor กับ Codex App เท่านั้น เครื่องมือ MW ยังเป็น shell script และยังไม่มีหลักฐานว่าทำงานบน Windows PowerShell โดยตรง หากงานต้องใช้ MW บน Windows ให้เปิดผ่าน WSL หรือ Git Bash และตรวจผลในสภาพแวดล้อมนั้นแยกต่างหาก

ทั้ง Mac และ Windows ให้ปิดแล้วเปิด Cursor หรือ Codex App ใหม่ 1 รอบหลังติดตั้ง แล้วลองพิมพ์ `Use New Chat`

หลังติดตั้ง พนักงานต้องรับไฟล์สิทธิ์ AI Portal ส่วนตัวจากแอดมินหนึ่งครั้งต่อเครื่อง
(ห้ามส่ง Token ในห้องแชทรวม) แล้วตั้งสิทธิ์ไฟล์:

```bash
chmod 600 ~/.hermes/.env
relay-doctor
```

Claude/Opus, Codex และ Grok จะวิ่งผ่าน AI Portal จึงไม่ต้องล็อกอินแยกแต่ละโปรแกรม
จากนั้นปิด-เปิดโปรแกรม AI ใหม่ 1 รอบ แล้วลองพิมพ์ `Use New Chat`

## วิธีตรวจเครื่องพนักงาน

```bash
curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/check-shortcuts.sh | bash
```

ผลที่ถูกต้อง:

```text
PASS registry_count               28
PASS skill_map_count              28
PASS index_count                  28
PASS prompt_md_count              32
RESULT: PASS
```

## ตัวติดตั้งทำอะไรบ้าง

| ขั้น | ทำอะไร | ต้องใช้สิทธิ์ผู้ดูแลไหม |
|---|---|:---:|
| 1 | คัดชุด Shortcut ไป `~/ObsidianVault/HermesAgent/` | ไม่ |
| 2 | ต่อ Claude Code ผ่าน `~/.claude/CLAUDE.md` | ไม่ |
| 3 | ต่อ Codex App ผ่าน `~/.codex/skills/prompt-shortcuts` | ไม่ |
| 4 | ต่อ Cursor ผ่านทางลัดชดเชยที่อยู่เดิม (เฉพาะ `--cursor`) | อาจขอ 1 ครั้ง |
| 5 | ติดตั้ง AI Relay และคำสั่งตรวจ (`relay-doctor`, `relay-status`, `gate-run`) | ไม่ |
| 6 | เพิ่ม `~/.local/bin` ให้ zsh/bash | ไม่ |

ตัวติดตั้งรันซ้ำได้ ไม่พัง (เขียนทับของเดิม)

## สำหรับพนักงานที่ทำงานบน VPS (บัญชี linux-nat)

หลังเจ้าของระบบอัปเดตชุดแจก ให้ใช้คำสั่งเดียวกับ Notebook บน VPS เพื่อให้คำสั่งลัดและ AI Relay เป็นรุ่นเดียวกัน:

```bash
curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.sh | bash
```

เหตุผล: VPS อ่าน Shortcut ผ่าน `/home/linux-nat/ObsidianVault/HermesAgent` ถ้าไม่ติดตั้งซ้ำหลัง sync อาจยังเห็น prompt รุ่นเก่าหรือไฟล์ Project OS ไม่ครบ

## สำหรับเจ้าของระบบ (อัปเดต Shortcut ใหม่)

```bash
bash sync-from-vault.sh   # ดึงของล่าสุดจาก vault มาใส่ payload
git add team-shortcuts/payload && git commit -m "sync shortcuts" && git push
```

แล้วทำ 2 จุด:

1. บอกพนักงานให้รันคำสั่ง `curl ... install-from-github.sh | bash` อีกครั้ง
2. รัน `install-from-github.sh` บน VPS หนึ่งครั้ง เพื่อให้เครื่องกลางเท่ากับ Notebook
