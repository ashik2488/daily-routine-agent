import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime, date

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

# Task Models
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

# Routes
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

@app.get("/api/settings")
def get_settings():
    return database.get_settings()

@app.post("/api/settings")
def save_settings(settings: Dict[str, Any]):
    database.update_settings(settings)
    return {"status": "success", "settings": database.get_settings()}

@app.post("/api/notifications/test")
def test_notification():
    notify("🌟 Daily Routine Agent Ready", "This is a test notification from your Daily Routine system. All systems are operational!")
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

@app.get("/api/stats")
def get_stats():
    return database.get_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
