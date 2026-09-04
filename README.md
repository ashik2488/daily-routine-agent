# 🤖 Daily Routine Agent - Autonomous AI Task Planner & Notification Hub

An intelligent, autonomous agentic system designed to turn bedtime brain dumps into structured, conflict-free daily schedules with automated morning briefings, pre-task countdown alerts, and multi-channel email/desktop notifications.

![Daily Routine Agent Logo](static/logo.png)

---

## 🌟 Key Features

- **🌙 Bedtime Natural Language Task Ingestor**: Dump thoughts and tasks freely before sleep. The NLP parser extracts start times, durations, energy levels, categories (`#work`, `#health`, `#learning`), and priorities (`P1`, `P2`, `P3`).
- **🤖 Autonomous Schedule Optimizer**: Allocates unscheduled tasks into high-energy productivity windows, detects schedule overcommitments, and selects the **Top 3 MITs (Most Important Tasks)**.
- **🌅 Multi-Channel Notification Engine**:
  - **Morning Briefing Digest**: Delivered to Windows Action Center & Email upon wake-up.
  - **Timed Countdown Reminders**: 10-minute pre-task alerts and real-time start notifications.
  - **Bedtime Reflection Nudge**: Prompts you before sleep to log tomorrow's routine.
  - **Native Windows Toast & Audio Chime**: Uses PowerShell WinRT notifications.
  - **HTML Email Dispatcher**: Responsive email summaries sent via SMTP.
- **⚡ Interactive Status Tracking**: One-click **Right Checkmark (✔)** and **Cross (✖)** controls to track completions and skips in real-time.
- **🚀 1-Click Silent Windows Background Daemon**: Runs autonomously on system boot without open terminal windows.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Scheduling**: APScheduler (Background Daemon)
- **Database**: SQLite3
- **Notifications**: Windows Toast API (WinRT), SMTPLib (HTML/MIME), Webhooks (Discord/Telegram)
- **Frontend**: Modern Responsive Single Page App (Vanilla JS, CSS Glassmorphism)

---

## 🚀 Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/your-username/daily-routine-agent.git
cd daily-routine-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the dashboard & background agent
start.bat
# Or run manually:
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

---

## 💻 CLI Usage

```bash
# Dump tasks before sleeping
python cli.py dump "- Wake up at 7am #routine\n- Deep work at 9am for 2h [P1]\n- Gym at 6pm"

# List tasks
python cli.py list

# Run AI optimization
python cli.py optimize
```
