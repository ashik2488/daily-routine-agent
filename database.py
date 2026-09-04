import sqlite3
import os
from datetime import datetime, date
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

    # Daily summaries
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_summaries (
        summary_date TEXT PRIMARY KEY,
        total_tasks INTEGER DEFAULT 0,
        completed_tasks INTEGER DEFAULT 0,
        reflection_notes TEXT DEFAULT '',
        agent_advice TEXT DEFAULT ''
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
        'email_recipient': '',
        'email_sender': '',
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

    conn.commit()
    conn.close()

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
    tasks = [dict(row) for row in rows]
    conn.close()
    return tasks

def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

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
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return True

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
    print('Database initialized with email settings.')
