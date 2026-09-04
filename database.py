import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routine.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        task_date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        duration_minutes INTEGER DEFAULT 30,
        priority TEXT DEFAULT 'P2',
        energy_level TEXT DEFAULT 'Medium',
        category TEXT DEFAULT 'Work',
        status TEXT DEFAULT 'pending',
        is_mit INTEGER DEFAULT 0,
        reminded_lead INTEGER DEFAULT 0,
        reminded_start INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')

    # Subtasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        is_completed INTEGER DEFAULT 0,
        estimated_minutes INTEGER DEFAULT 15,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    )
    ''')

    # Habits table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        icon TEXT DEFAULT '🔥',
        frequency TEXT DEFAULT 'daily',
        target_days INTEGER DEFAULT 7,
        streak_count INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    ''')

    # Habit Logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        status TEXT DEFAULT 'completed',
        logged_at TEXT NOT NULL,
        UNIQUE(habit_id, log_date),
        FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
    )
    ''')

    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    # Notification logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        channel TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        status TEXT DEFAULT 'sent'
    )
    ''')

    # Default settings
    default_settings = {
        'morning_briefing_time': '07:30',
        'evening_planning_time': '22:00',
        'notify_lead_minutes': '10',
        'enable_windows_toast': 'true',
        'enable_audio_chime': 'true',
        'enable_email_notifications': 'true',
        'email_recipient': 'ashikchowdhury2488@gmail.com',
        'email_sender': 'fitnesspoint943@gmail.com',
        'email_smtp_password': '',
        'email_smtp_host': 'smtp.gmail.com',
        'email_smtp_port': '587',
        'discord_webhook_url': '',
        'telegram_bot_token': '',
        'telegram_chat_id': '',
        'gemini_api_key': '',
        'user_name': 'Champion'
    }

    for k, v in default_settings.items():
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))

    # Insert default starter habits if empty
    cursor.execute('SELECT COUNT(*) as count FROM habits')
    if cursor.fetchone()['count'] == 0:
        now = datetime.now().isoformat()
        default_habits = [
            ('Drink 2.5L Water', '💧', 0),
            ('Morning 10m Stretch / Exercise', '🧘', 0),
            ('Deep Focus Block (No Phone)', '⚡', 0),
            ('Read 15 Pages', '📖', 0),
            ('Log Bedtime Routine', '🌙', 0)
        ]
        for title, icon, streak in default_habits:
            cursor.execute('INSERT INTO habits (title, icon, streak_count, created_at) VALUES (?, ?, ?, ?)',
                           (title, icon, streak, now))

    conn.commit()
    conn.close()

# Tasks CRUD
def create_task(data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO tasks (
        title, description, task_date, start_time, end_time,
        duration_minutes, priority, energy_level, category,
        status, is_mit, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('title'),
        data.get('description', ''),
        data.get('task_date', date.today().isoformat()),
        data.get('start_time'),
        data.get('end_time'),
        data.get('duration_minutes', 30),
        data.get('priority', 'P2'),
        data.get('energy_level', 'Medium'),
        data.get('category', 'Work'),
        data.get('status', 'pending'),
        1 if data.get('is_mit') else 0,
        now,
        now
    ))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks_for_date(task_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM tasks
    WHERE task_date = ?
    ORDER BY 
        CASE WHEN start_time IS NULL THEN 1 ELSE 0 END,
        start_time ASC,
        priority ASC,
        id ASC
    ''', (task_date,))
    rows = cursor.fetchall()
    tasks = []
    for r in rows:
        td = dict(r)
        # Fetch subtasks for each task
        cursor.execute('SELECT * FROM subtasks WHERE task_id = ? ORDER BY id ASC', (td['id'],))
        td['subtasks'] = [dict(sr) for sr in cursor.fetchall()]
        tasks.append(td)
    conn.close()
    return tasks

def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    task_dict = dict(row)
    cursor.execute('SELECT * FROM subtasks WHERE task_id = ? ORDER BY id ASC', (task_id,))
    task_dict['subtasks'] = [dict(sr) for sr in cursor.fetchall()]
    conn.close()
    return task_dict

def update_task(task_id: int, data: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    fields = []
    values = []
    for k, v in data.items():
        if k in ['title', 'description', 'task_date', 'start_time', 'end_time', 
                 'duration_minutes', 'priority', 'energy_level', 'category', 
                 'status', 'is_mit', 'reminded_lead', 'reminded_start']:
            fields.append(f"{k} = ?")
            values.append(v)
            
    if not fields:
        conn.close()
        return False
        
    fields.append('updated_at = ?')
    values.append(now)
    values.append(task_id)
    
    set_clause = ', '.join(fields)
    query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True

def delete_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subtasks WHERE task_id = ?', (task_id,))
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return True

# Subtasks CRUD
def create_subtask(task_id: int, title: str, estimated_minutes: int = 15) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO subtasks (task_id, title, is_completed, estimated_minutes, created_at)
    VALUES (?, ?, 0, ?, ?)
    ''', (task_id, title, estimated_minutes, now))
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub_id

def toggle_subtask(subtask_id: int, is_completed: bool) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE subtasks SET is_completed = ? WHERE id = ?', (1 if is_completed else 0, subtask_id))
    conn.commit()
    conn.close()
    return True

def delete_subtask(subtask_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM subtasks WHERE id = ?', (subtask_id,))
    conn.commit()
    conn.close()
    return True

# Habits CRUD & Streaks
def get_habits_for_date(target_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT h.*, 
           CASE WHEN hl.id IS NOT NULL THEN 1 ELSE 0 END as is_completed
    FROM habits h
    LEFT JOIN habit_logs hl ON h.id = hl.habit_id AND hl.log_date = ?
    ORDER BY h.id ASC
    ''', (target_date,))
    rows = cursor.fetchall()
    habits = [dict(r) for r in rows]
    conn.close()
    return habits

def toggle_habit(habit_id: int, log_date: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if already completed on this date
    cursor.execute('SELECT id FROM habit_logs WHERE habit_id = ? AND log_date = ?', (habit_id, log_date))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('DELETE FROM habit_logs WHERE id = ?', (existing['id'],))
        is_completed = False
    else:
        cursor.execute('''
        INSERT INTO habit_logs (habit_id, log_date, status, logged_at)
        VALUES (?, ?, 'completed', ?)
        ''', (habit_id, log_date, datetime.now().isoformat()))
        is_completed = True

    # Recalculate streak
    cursor.execute('SELECT log_date FROM habit_logs WHERE habit_id = ? ORDER BY log_date DESC', (habit_id,))
    logs = [r['log_date'] for r in cursor.fetchall()]
    
    current_streak = 0
    check_d = date.today()
    logs_set = set(logs)
    
    while check_d.isoformat() in logs_set:
        current_streak += 1
        check_d -= timedelta(days=1)
        
    cursor.execute('UPDATE habits SET streak_count = ? WHERE id = ?', (current_streak, habit_id))
    conn.commit()
    conn.close()
    return {"habit_id": habit_id, "is_completed": is_completed, "streak": current_streak}

def create_habit(title: str, icon: str = "🔥") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('INSERT INTO habits (title, icon, created_at) VALUES (?, ?, ?)', (title, icon, now))
    habit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return habit_id

def delete_habit(habit_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM habit_logs WHERE habit_id = ?', (habit_id,))
    cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
    conn.commit()
    conn.close()
    return True

# Analytics
def get_weekly_analytics() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today()
    
    # Last 7 days completion
    days_data = []
    for i in range(6, -1, -1):
        d_str = (today - timedelta(days=i)).isoformat()
        cursor.execute('''
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
               SUM(duration_minutes) as total_mins
        FROM tasks WHERE task_date = ?
        ''', (d_str,))
        r = cursor.fetchone()
        days_data.append({
            "date": d_str,
            "day": (today - timedelta(days=i)).strftime("%a"),
            "total": r['total'] or 0,
            "completed": r['completed'] or 0,
            "hours": round((r['total_mins'] or 0) / 60, 1)
        })

    # Category distribution (last 30 days)
    cursor.execute('''
    SELECT category, COUNT(*) as count, SUM(duration_minutes) as mins
    FROM tasks
    GROUP BY category
    ''')
    cat_rows = cursor.fetchall()
    categories = {r['category']: r['count'] for r in cat_rows}

    # Overall streak & score
    total_tasks = sum(d['total'] for d in days_data)
    total_done = sum(d['completed'] for d in days_data)
    rate = round((total_done / total_tasks * 100)) if total_tasks > 0 else 100

    conn.close()
    return {
        "days": days_data,
        "categories": categories,
        "weekly_completion_rate": rate,
        "total_weekly_tasks": total_tasks,
        "total_weekly_completed": total_done
    }

def get_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM settings')
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def update_settings(settings: Dict[str, str]):
    conn = get_connection()
    cursor = conn.cursor()
    for k, v in settings.items():
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, str(v)))
    conn.commit()
    conn.close()

def log_notification(title: str, message: str, channel: str, status: str = 'sent'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO notification_logs (title, message, channel, sent_at, status)
    VALUES (?, ?, ?, ?, ?)
    ''', (title, message, channel, datetime.now().isoformat(), status))
    conn.commit()
    conn.close()

def get_notification_logs(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notification_logs ORDER BY sent_at DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN status = "completed" THEN 1 ELSE 0 END) as completed FROM tasks')
    all_time = cursor.fetchone()
    
    today = date.today().isoformat()
    cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN status = "completed" THEN 1 ELSE 0 END) as completed FROM tasks WHERE task_date = ?', (today,))
    today_stats = cursor.fetchone()
    
    conn.close()
    
    return {
        'all_time_total': all_time['total'] or 0,
        'all_time_completed': all_time['completed'] or 0,
        'today_total': today_stats['total'] or 0,
        'today_completed': today_stats['completed'] or 0
    }

if __name__ == '__main__':
    init_db()
    print('Database initialized with subtasks and habits.')
