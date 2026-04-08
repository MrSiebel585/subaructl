# subaructl
AI-Assisted Subaru WRX ECU Tuning System (EJ205)


# subaructl

**Subaru ECU / OBD Unified CLI for Linux**

A unified command-line toolkit for Subaru diagnostics, logging, dashboards, and ECU patching—built for Linux users who want full control without juggling multiple tools.

---

## 🔥 What It Does

- 🔍 **Diagnostics** – one command to verify your entire environment
- 📡 **Live Logging** – SSM + OBD data capture
- 📊 **Dashboard** – real-time visualization via Flask
- 🧠 **AI Logging** – optional Ollama-powered analysis
- ⚙️ **ECU Patching** – safe, controlled patch generation

---

## ⚡ Quick Start (2 minutes)

```bash
git clone https://github.com/MrSiebel585/subaructl.git
cd subaructl
chmod +x subaructl
./subaructl doctor
