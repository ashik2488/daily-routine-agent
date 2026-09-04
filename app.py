import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import database
from agent import agent_instance
from scheduler import scheduler_instance
from notifier import notify, send_email_notification

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    database.init_db()
    scheduler_instance.start()
    yield
    # Shutdown
    scheduler_instance.stop()

app = FastAPI(title="Daily Routine Agent", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Daily Routine Agent API is running."}

# ───── Pydantic Models ─────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    task_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = 30
    priority: Optional[str] = "P2"
    energy_level: Optional[str] = "Medium"
    category: Optional[str] = "Work"
    is_mit: Optional[bool] = False

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    priority: Optional[str] = None
    energy_level: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_mit: Optional[bool] = None

class BulkNightEntry(BaseModel):
    raw_text: str
    target_date: Optional[str] = None

class SubtaskCreate(BaseModel):
    task_id: int
    title: str
    estimated_minutes: Optional[int] = 15

class HabitCreate(BaseModel):
    title: str
    icon: Optional[str] = "⭐"
    frequency: Optional[str] = "daily"
    target_days: Optional[int] = 7

# ───── Task Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/tasks")
def list_tasks(task_date: Optional[str] = Query(None, alias="date")):
    if not task_date:
        task_date = date.today().isoformat()
    tasks = database.get_tasks_for_date(task_date)
    return {"date": task_date, "tasks": tasks, "count": len(tasks)}

@app.post("/api/tasks")
def add_task(task: TaskCreate):
    task_dict = task.dict()
    if not task_dict.get('task_date'):
        task_dict['task_date'] = date.today().isoformat()
    task_id = database.create_task(task_dict)
    return {"status": "success", "id": task_id, "task": database.get_task_by_id(task_id)}

@app.put("/api/tasks/{task_id}")
def edit_task(task_id: int, updates: TaskUpdate):
    data = {k: v for k, v in updates.dict().items() if v is not None}
    success = database.update_task(task_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or nothing updated")
    return {"status": "success", "task": database.get_task_by_id(task_id)}

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    success = database.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "id": task_id}

@app.post("/api/tasks/bulk-night-entry")
def bulk_night_entry(payload: BulkNightEntry):
    target_date = payload.target_date
    if not target_date:
        now = datetime.now()
        if now.hour >= 19:
            target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            target_date = now.strftime("%Y-%m-%d")

    parsed = agent_instance.parse_natural_language_tasks(payload.raw_text, target_date)
    created_ids = []
    for item in parsed:
        t_id = database.create_task(item)
        created_ids.append(t_id)

    return {
        "status": "success",
        "target_date": target_date,
        "tasks_created": len(created_ids),
        "tasks": database.get_tasks_for_date(target_date)
    }

# ───── AI Task Decomposition ───────────────────────────────────────────────────

@app.post("/api/tasks/{task_id}/ai-decompose")
def ai_decompose_task(task_id: int):
    task = database.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    subtasks = agent_instance.decompose_task_into_subtasks(
        task["title"], task.get("duration_minutes", 30)
    )
    created = []
    for st in subtasks:
        sid = database.create_subtask(task_id, st["title"], st["estimated_minutes"])
        created.append({"id": sid, "title": st["title"],
                         "estimated_minutes": st["estimated_minutes"], "is_completed": False})

    return {"status": "success", "task_id": task_id, "subtasks": created}

# ───── Subtask Endpoints ───────────────────────────────────────────────────────

@app.get("/api/tasks/{task_id}/subtasks")
def get_task_subtasks(task_id: int):
    task = database.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"subtasks": task.get("subtasks", [])}

@app.post("/api/subtasks")
def create_subtask_endpoint(payload: SubtaskCreate):
    sid = database.create_subtask(payload.task_id, payload.title,
                                   payload.estimated_minutes or 15)
    return {"status": "success", "id": sid}

@app.put("/api/subtasks/{subtask_id}/toggle")
def toggle_subtask_endpoint(subtask_id: int):
    # Read current state then toggle
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_completed FROM subtasks WHERE id = ?", (subtask_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Subtask not found")
    new_state = not bool(row["is_completed"])
    database.toggle_subtask(subtask_id, new_state)
    return {"status": "success", "is_completed": new_state}

@app.delete("/api/subtasks/{subtask_id}")
def delete_subtask_endpoint(subtask_id: int):
    database.delete_subtask(subtask_id)
    return {"status": "success"}

# ───── Habit Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/habits")
def list_habits(log_date: Optional[str] = Query(None, alias="date")):
    if not log_date:
        log_date = date.today().isoformat()
    habits = database.get_habits_for_date(log_date)
    # Normalize: rename is_completed → today_done for frontend consistency
    for h in habits:
        h["today_done"] = bool(h.get("is_completed", 0))
    return {"date": log_date, "habits": habits}

@app.post("/api/habits")
def create_habit_endpoint(payload: HabitCreate):
    hid = database.create_habit(payload.title, payload.icon or "⭐")
    return {"status": "success", "id": hid}

@app.delete("/api/habits/{habit_id}")
def delete_habit_endpoint(habit_id: int):
    database.delete_habit(habit_id)
    return {"status": "success"}

@app.post("/api/habits/{habit_id}/toggle")
def toggle_habit_endpoint(habit_id: int, log_date: Optional[str] = Query(None, alias="date")):
    if not log_date:
        log_date = date.today().isoformat()
    result = database.toggle_habit(habit_id, log_date)
    return {"status": "success", "new_status": "completed" if result.get("is_completed") else "pending"}

# ───── Analytics Endpoints ─────────────────────────────────────────────────────

@app.get("/api/analytics/weekly")
def get_weekly_analytics():
    analytics = database.get_weekly_analytics()
    days_data = analytics.get("days", [])
    report = agent_instance.generate_weekly_analytics_report(days_data)
    return {"status": "success", "days": days_data, "report": report}

# ───── Agent & Scheduler ───────────────────────────────────────────────────────

@app.post("/api/agent/optimize")
def optimize_routine(payload: Dict[str, str] = Body(...)):
    task_date = payload.get("date", date.today().isoformat())
    result = agent_instance.optimize_schedule(task_date)
    return result

@app.get("/api/agent/briefing")
def get_morning_briefing(task_date: Optional[str] = Query(None, alias="date")):
    if not task_date:
        task_date = date.today().isoformat()
    return agent_instance.generate_morning_briefing(task_date)

@app.get("/api/agent/reflection")
def get_evening_reflection(task_date: Optional[str] = Query(None, alias="date")):
    if not task_date:
        task_date = date.today().isoformat()
    return agent_instance.generate_evening_reflection(task_date)

# ───── Settings ────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    return database.get_settings()

@app.post("/api/settings")
def save_settings(settings: Dict[str, Any]):
    database.update_settings(settings)
    return {"status": "success", "settings": database.get_settings()}

# ───── Notifications ───────────────────────────────────────────────────────────

@app.post("/api/notifications/test")
def test_notification():
    notify("Daily Routine Agent Ready", "This is a test notification from your Daily Routine system. All systems are operational!")
    return {"status": "success", "message": "Notification dispatched."}

@app.post("/api/notifications/test-email")
def test_email(payload: Optional[Dict[str, str]] = None):
    settings = database.get_settings()
    recipient = (payload and payload.get("recipient")) or settings.get("email_recipient")
    if not recipient:
        raise HTTPException(status_code=400, detail="Please provide or save a recipient email address first.")

    success, msg = send_email_notification(
        recipient,
        "Test Email from Daily Routine Agent",
        "Hello! Your email notification setup is working perfectly. You will receive your morning routine briefings, bedtime planning prompts, and task reminders right here."
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {msg}")
    return {"status": "success", "message": f"Test email sent to {recipient}!"}

@app.get("/api/notifications/logs")
def get_logs():
    return database.get_notification_logs(30)

# ───── Stats ───────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    return database.get_stats()

# ───── PWA ────────────────────────────────────────────────────────────────────

@app.get("/manifest.json")
async def get_manifest():
    mf = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(mf):
        return FileResponse(mf, media_type="application/manifest+json")
    return JSONResponse({"error": "manifest not found"}, status_code=404)

@app.get("/sw.js")
async def get_sw():
    sw = os.path.join(STATIC_DIR, "sw.js")
    if os.path.exists(sw):
        return FileResponse(sw, media_type="application/javascript")
    return JSONResponse({"error": "service worker not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
