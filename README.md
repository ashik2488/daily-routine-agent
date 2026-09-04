# 🤖 Daily Routine Agent - Autonomous AI Task Planner & Notification Hub

An intelligent, autonomous agentic desktop app designed to turn bedtime brain dumps into structured, conflict-free daily schedules with automated morning briefings, pre-task countdown alerts, habit tracking, Pomodoro focus sessions, and multi-channel email/desktop notifications.

![Daily Routine Agent Logo](static/logo.png)

---

## 🌟 Key Features

- **🌙 Bedtime Natural Language Task Ingestor**: Dump thoughts and tasks freely before sleep. The NLP parser extracts start times, durations, energy levels, categories (`#work`, `#health`, `#learning`), and priorities (`P1`, `P2`, `P3`).
- **🎙️ Voice Input Task Ingestor**: Speak your bedtime routine directly using built-in speech recognition.
- **⚡ AI Task Breakdown (Subtask Decomposition)**: One-click `⚡ AI Break Down` decomposing complex tasks into actionable 3–5 step checklists with estimated durations.
- **🔥 Daily Habit Tracker & Streaks**: Pre-loaded and custom habits with daily toggle checkmarks and consecutive streak counter.
- **🍅 Pomodoro Focus Timer with Web Audio Ambient Soundscapes**: 25/5/15-minute cycles with real-time browser-synthesized ambient audio (Rain, Brown Noise, Cafe).
- **📊 7-Day Analytics & AI Strategic Review**: Visual HTML5 Canvas completion chart accompanied by AI performance commentary and consistency scores.
- **🤖 Autonomous Schedule Optimizer**: Allocates unscheduled tasks into high-energy productivity windows, detects schedule overcommitments, and selects the **Top 3 MITs (Most Important Tasks)**.
- **🌅 Multi-Channel Notification Engine**:
  - **Morning Briefing Digest**: Delivered to Windows Action Center & Email upon wake-up.
  - **Timed Countdown Reminders**: 10-minute pre-task alerts and real-time start notifications.
  - **Bedtime Reflection Nudge**: Prompts you before sleep to log tomorrow's routine.
  - **Native Windows Toast & Audio Chime**: Uses PowerShell WinRT notifications.
  - **HTML Email Dispatcher**: Responsive email summaries sent via SMTP (supports multi-recipient).
- **⚡ Interactive Status Tracking**: One-click **Right Checkmark (✔)** and **Cross (✖)** controls to track completions and skips in real-time.
- **📱 PWA & Dedicated App Window Mode**: Supports offline caching via Service Worker, PWA manifest installation, and standalone desktop launcher without browser toolbar borders.
- **🚀 1-Click Silent Windows Background Daemon**: Runs autonomously on system boot without open terminal windows.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Scheduling**: APScheduler (Background Daemon)
- **Database**: SQLite3 (Tasks, Subtasks, Habits, Habit Logs, Settings, Summaries)
- **Notifications**: Windows Toast API (WinRT), SMTPLib (HTML/MIME), Webhooks (Discord/Telegram)
- **Audio & Speech**: Web Audio API (ambient synthesis), Web Speech Recognition API
- **Frontend**: Modern Responsive Single Page App (Vanilla JS, CSS Glassmorphism, Service Worker PWA)

---

## 🚀 Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/ashik2488/daily-routine-agent.git
cd daily-routine-agent

# 2. Launch the dashboard & background agent
start.bat
# Or launch directly in dedicated app window:
open_app.vbs
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

---

## 🧪 Testing

```bash
python test_suite.py
```
