<div align="center">

<img src="https://i.postimg.cc/vZ968zNW/Screenshot-2026-10-10-3.png" alt="JoomlaChecker Banner" width="100%"/>

# 🎯 JoomlaChecker — ULTIMATE EDITION

### 🚀 Joomla Admin Login Checker — v9.0

<img src="https://img.shields.io/badge/Version-9.0-ff00ff?style=for-the-badge&logo=joomla&logoColor=white"/>
<img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-00d9ff?style=for-the-badge"/>
<img src="https://img.shields.io/badge/License-Educational-red?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Author-HACKFUT-00ff88?style=for-the-badge"/>

<br/>

<img src="https://img.shields.io/badge/Joomla-1.0%20→%205.x-orange?style=flat-square"/>
<img src="https://img.shields.io/badge/Multi--Payload-7%20Strategies-purple?style=flat-square"/>
<img src="https://img.shields.io/badge/Multi--Threaded-10%20Workers-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/Version--Aware-✔-brightgreen?style=flat-square"/>

<br/><br/>

**🔥 The only Joomla checker that auto-detects the version, generates 7 tailored payloads, and verifies across multiple protected paths — Strict anti-false-positive 🔥**

</div>

---

## 📸 Terminal Preview

<div align="center">
<img src="https://i.postimg.cc/vZ968zNW/Screenshot-2026-10-10-3.png" alt="Terminal Launch" width="90%"/>
<br/>
<i>🚀 Tool launch — Colorful interface & ASCII banner</i>
</div>

<br/>

<div align="center">
<img src="https://i.postimg.cc/63H8b1yZ/Screenshot-2026-10-10-4.png" alt="Results" width="90%"/>
<br/>
<i>✅ Live results — Version detection + payload used</i>
</div>

<br/>

<div align="center">
<img src="https://i.postimg.cc/WzChTFmW/Screenshot-2026-10-10-5.png" alt="Joomla Panel" width="90%"/>
<br/>
<i>🎯 Joomla panel found by the tool — Manually verified</i>
</div>

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🧠 Intelligence
- ✅ **Multi-Version** — Supports Joomla **1.0 → 5.x**
- ✅ **Auto-detection** of version (HTML + Manifest + legacy)
- ✅ **7 Payloads** generated per credential
- ✅ **Adaptive Threshold** (2 markers for old / 3 for modern)

</td>
<td width="50%" valign="top">

### 🛡️ Reliability
- ✅ **Version-aware cookies** (`jos_session` vs `joomla_user_state`)
- ✅ **Version-aware paths** (`index2.php` vs `index.php`)
- ✅ **Multi-path verification** (5-6 protected paths)
- ✅ **Strict anti-false-positive** logic

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚡ Performance
- ✅ **Multi-threading** (10 workers by default)
- ✅ **Fresh session** per payload
- ✅ **CSRF token** auto-extraction
- ✅ **Quick check** + Full verification

</td>
<td width="50%" valign="top">

### 🎨 Interface
- ✅ **Colorful** ASCII banner
- ✅ **Colorama** output (green = success / red = fail)
- ✅ Separate files `successful_logins.txt` / `failed_logins.txt`
- ✅ Final stats (time, counters)

</td>
</tr>
</table>

---

## 🎯 How It Works

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1 — Version Detection                            │
│    • HTML admin  •  joomla.xml manifest  •  legacy     │
├─────────────────────────────────────────────────────────┤
│  STEP 2 — Locate Login Form                            │
│    • index2.php (1.0/1.5)  •  index.php (3.x+)         │
├─────────────────────────────────────────────────────────┤
│  STEP 3 — CSRF Token Extraction                        │
│    • Hidden input 32+ chars                            │
├─────────────────────────────────────────────────────────┤
│  STEP 4 — Generate 7 Payloads                          │
│    1.5-3.x | 4.x-5.x | 1.5 legacy | 1.0 | hybrid ...   │
├─────────────────────────────────────────────────────────┤
│  STEP 5 — Test + Verification                          │
│    • Quick check login response                        │
│    • Full verify on 5-6 protected paths                │
├─────────────────────────────────────────────────────────┤
│  STEP 6 — Verdict                                      │
│    ✅ REAL  |  ❌ FAIL  (with detailed reason)          │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Requirements
- **Python 3.8+**
- Up-to-date `pip`

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/HackfutSecRoot/JoomlaChecker.git
cd JoomlaChecker

# 2. Install dependencies
pip install requests urllib3 colorama

# 3. Run the tool
python3 joomla_checker.py
```

---

## 🚀 Usage

### 1️⃣ Input File Format

Create a file (e.g. `targets.txt`) with the following format:

```
https://site1.com#admin@password123
https://site2.com/joomla#administrator@pass456
https://site3.com#root@toor
```

> **Format:** `URL#USERNAME@PASSWORD`

### 2️⃣ Launch the Checker

```bash
python3 joomla_checker.py

# Then enter the file path:
Give me your file: targets.txt
```

### 3️⃣ Results

| File | Content |
|------|---------|
| 🟢 `successful_logins.txt` | Confirmed logins with version + payload |
| 🔴 `failed_logins.txt` | Failed logins with reason |

**Example of a successful output:**
```
[✔ REAL]  admin@password123 | https://site1.com | v3.x | payload=v1.5-3.x | admin_content_v3.x
```

**Example of a failed output:**
```
[✗ FAIL] admin@wrongpass | https://site1.com | v3.x | tried 7 payloads
```

---

## 🧩 Joomla Version Compatibility

| Version | Login Path | Cookie | Payload |
|---------|-----------|--------|---------|
| **1.0** | `index2.php` | `sessioncookie` / `mos_*` | `user` + `pass` |
| **1.5** | `index2.php` | `jos_session` | `username` + `passwd` |
| **1.6 / 1.7** | `index.php` | `jos_session` | `username` + `passwd` |
| **2.5** | `index.php` | `jos_session` | `username` + `passwd` |
| **3.x** | `index.php` | `joomla_user_state` | `username` + `passwd` |
| **4.x** | `index.php` | `joomla_user_state` | `username` + `password` |
| **5.x** | `index.php` | `joomla_user_state` | `username` + `password` |

---

## 🛡️ Verified Protected Paths

```yaml
Modern (3.x → 5.x):
  - /administrator/index.php?option=com_users&view=users
  - /administrator/index.php?option=com_config
  - /administrator/index.php?option=com_users&task=view
  - /administrator/index.php?option=com_content
  - /administrator/index.php?option=com_media

Legacy (1.0 / 1.5):
  - /administrator/index2.php?option=com_content
  - /administrator/index2.php?option=com_users
  - /administrator/index2.php?option=com_admin
```

---

## ⚙️ Configuration

Open `joomla_checker.py` and modify:

```python
MAX_THREADS = 10                    # Number of threads
SUCCESS_FILE = "successful_logins.txt"
FAILED_FILE  = "failed_logins.txt"
```

---

## 📊 Project Stats

<div align="center">

| Metric | Value |
|:------:|:-----:|
| 🎯 Supported Joomla versions | **1.0 → 5.x** |
| 🧬 Payloads per credential | **7** |
| 🛡️ Protected paths verified | **5-6** |
| ⚡ Parallel threads | **10** |
| 🎨 Admin markers (per version) | **6-11** |

</div>

---

## 📞 Contact & Socials

<div align="center">

### 👤 **HACKFUT**

[![Telegram Channel 1](https://img.shields.io/badge/📢_Channel_1-Join-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/+gsrpvshwGUc5MzI0)
[![Telegram Channel 2](https://img.shields.io/badge/📢_Channel_2-LinxProdXs404-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/LinxProdXs404)
[![Telegram DM](https://img.shields.io/badge/💬_DM-@HackfutS3c-00ff88?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/HackfutS3c)
[![Pastebin](https://img.shields.io/badge/📋_Pastebin-hackfut-000000?style=for-the-badge&logo=linux&logoColor=white)](https://pastebin.com/u/hackfut)

<br/>

### 🔗 Useful Links

- 📢 **Channel 1** — https://t.me/+gsrpvshwGUc5MzI0
- 📢 **Channel 2** — https://t.me/LinxProdXs404
- 🤖 **Bot/ULP** — [@ulp_CLOUD1](https://t.me/ulp_CLOUD1)
- 📝 **Post 1** — https://t.me/LinxProdXs404/249
- 📝 **Post 2** — https://t.me/LinxProdXs404/541
- 📋 **Pastebin** — https://pastebin.com/u/hackfut
- 💬 **DM** — [@HackfutS3c](https://t.me/HackfutS3c)

</div>

---

## ⚠️ DISCLAIMER

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  LEGAL WARNING                                           ║
║                                                              ║
║  This tool is provided for EDUCATIONAL and SECURITY          ║
║  RESEARCH purposes only.                                     ║
║                                                              ║
║  • Any use against systems without prior written consent     ║
║    is ILLEGAL.                                               ║
║  • The author is NOT responsible for any abusive or          ║
║    unlawful use.                                             ║
║  • Respect the laws of your country.                         ║
║                                                              ║
║  🛡️ Test ONLY on your own systems                            ║
║     or within an AUTHORIZED pentest engagement.              ║
╚══════════════════════════════════════════════════════════════╝
```

**BY USING THIS TOOL YOU AGREE TO THESE TERMS.**

</div>

---

<div align="center">

### ⭐ If this project helped you, drop a star! ⭐

<img src="https://img.shields.io/github/stars/HackfutSecRoot/JoomlaChecker?style=social"/>
<img src="https://img.shields.io/github/forks/HackfutSecRoot/JoomlaChecker?style=social"/>

<br/><br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,13,14,15,16&height=120&section=footer&text=Made%20with%20%E2%9D%A4%EF%B8%8F%20by%20HACKFUT&fontSize=28&fontColor=ffffff"/>

</div>
