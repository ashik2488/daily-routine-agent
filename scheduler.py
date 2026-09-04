import threading
import time
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_tasks_for_date, update_task, get_settings
from agent import agent_instance
from notifier import notify

class RoutineScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.last_morning_sent_date = None
        self.last_evening_sent_date = None

    def check_and_notify_tasks(self):
        """
        Periodically checks for tasks needing alerts, morning briefing, or evening planning reminders.
        """
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")

        settings = get_settings()
        morning_time = settings.get('morning_briefing_time', '07:30')
        evening_time = settings.get('evening_planning_time', '22:00')
        lead_minutes = int(settings.get('notify_lead_minutes', '10'))

        # 1. Morning Briefing Notification
        if current_time_str == morning_time and self.last_morning_sent_date != today_str:
            briefing = agent_instance.generate_morning_briefing(today_str)
            notify(briefing['title'], briefing['message'], "morning")
            self.last_morning_sent_date = today_str

        # 2. Evening Planning Notification
        if current_time_str == evening_time and self.last_evening_sent_date != today_str:
            reflection = agent_instance.generate_evening_reflection(today_str)
            notify(reflection['title'], reflection['message'], "evening")
            self.last_evening_sent_date = today_str

        # 3. Individual Task Reminders
        tasks = get_tasks_for_date(today_str)
        for t in tasks:
            if not t.get('start_time') or t.get('status') == 'completed':
                continue

            try:
                task_start_dt = datetime.strptime(f"{today_str} {t['start_time']}", "%Y-%m-%d %H:%M")
            except Exception:
                continue

            diff_seconds = (task_start_dt - now).total_seconds()
            diff_minutes = diff_seconds / 60.0

            # Lead Reminder (e.g. 10 minutes before)
            if 0 < diff_minutes <= lead_minutes and not t.get('reminded_lead'):
                mins_left = max(1, int(round(diff_minutes)))
                mit_tag = "⭐ [MIT] " if t.get('is_mit') else ""
                title = f"⏰ Upcoming Task ({mins_left}m left)"
                msg = f"{mit_tag}{t['title']}\nStarts at {t['start_time']} ({t.get('category', 'Work')})"
                notify(title, msg, "reminder")
                update_task(t['id'], {'reminded_lead': 1})

            # Exact Start Time Reminder (0 to 2 minutes past start)
            if -2 <= diff_minutes <= 0 and not t.get('reminded_start'):
                mit_tag = "⭐ [MIT] " if t.get('is_mit') else ""
                title = f"🚀 Task Starting Now!"
                msg = f"{mit_tag}{t['title']}\nDuration: {t.get('duration_minutes', 30)} mins"
                notify(title, msg, "start")
                update_task(t['id'], {'reminded_start': 1})

    def start(self):
        if not self.scheduler.running:
            self.scheduler.add_job(self.check_and_notify_tasks, 'interval', seconds=30, id='routine_checker')
            self.scheduler.start()
            print("RoutineScheduler background daemon started (checking every 30s).")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("RoutineScheduler stopped.")

scheduler_instance = RoutineScheduler()
