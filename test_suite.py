import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def run_tests():
    print("===========================================")
    print("  RUNNING DAILY ROUTINE AGENT TEST SUITE   ")
    print("===========================================\n")
    
    # 1. Root dashboard & PWA
    r = client.get("/")
    assert r.status_code == 200
    r_man = client.get("/manifest.json")
    assert r_man.status_code == 200
    r_sw = client.get("/sw.js")
    assert r_sw.status_code == 200
    print("[PASS] GET / & PWA assets (manifest.json, sw.js)")

    # 2. Add task
    r = client.post("/api/tasks", json={
        "title": "Build Architecture Module",
        "task_date": "2026-09-06",
        "start_time": "14:00",
        "duration_minutes": 60,
        "priority": "P1",
        "category": "Work"
    })
    assert r.status_code == 200
    task_id = r.json()["id"]
    print(f"[PASS] POST /api/tasks (Created task #{task_id})")

    # 3. AI Task Decomposition into Subtasks
    r = client.post(f"/api/tasks/{task_id}/ai-decompose")
    assert r.status_code == 200
    subtasks = r.json().get("subtasks", [])
    assert len(subtasks) > 0
    print(f"[PASS] POST /api/tasks/{task_id}/ai-decompose (Generated {len(subtasks)} subtasks)")

    # 4. Toggle Subtask
    sid = subtasks[0]["id"]
    r = client.put(f"/api/subtasks/{sid}/toggle")
    assert r.status_code == 200
    assert r.json().get("is_completed") is True
    print(f"[PASS] PUT /api/subtasks/{sid}/toggle (Toggled subtask completion)")

    # 5. Bulk Night Entry
    r = client.post("/api/tasks/bulk-night-entry", json={
        "raw_text": "- Wake up at 6:30 AM #routine\n- Morning Run for 30 mins [P1]\n- Deep Work 10am for 2 hrs",
        "target_date": "2026-09-06"
    })
    assert r.status_code == 200
    print(f"[PASS] POST /api/tasks/bulk-night-entry (Created {r.json()['tasks_created']} tasks)")

    # 6. List tasks
    r = client.get("/api/tasks?date=2026-09-06")
    assert r.status_code == 200
    print(f"[PASS] GET /api/tasks (Found {len(r.json()['tasks'])} tasks)")

    # 7. Optimize routine
    r = client.post("/api/agent/optimize", json={"date": "2026-09-06"})
    assert r.status_code == 200
    print("[PASS] POST /api/agent/optimize (AI schedule allocated & advice created)")

    # 8. Habits Tracker & Streaks
    r = client.get("/api/habits?date=2026-09-06")
    assert r.status_code == 200
    habits = r.json().get("habits", [])
    assert len(habits) >= 1
    hid = habits[0]["id"]
    r_toggle = client.post(f"/api/habits/{hid}/toggle?date=2026-09-06")
    assert r_toggle.status_code == 200
    print(f"[PASS] Habits API & Streak Toggle (Loaded {len(habits)} habits, toggled habit #{hid})")

    # 9. Weekly Analytics & AI Natural Language Report
    r = client.get("/api/analytics/weekly")
    assert r.status_code == 200
    analytics = r.json()
    assert len(analytics.get("days", [])) == 7
    assert len(analytics.get("report", "")) > 0
    print("[PASS] GET /api/analytics/weekly (7-day chart data + AI narrative summary)")

    # 10. Briefing & Reflection
    r = client.get("/api/agent/briefing?date=2026-09-06")
    assert r.status_code == 200
    r = client.get("/api/agent/reflection?date=2026-09-06")
    assert r.status_code == 200
    print("[PASS] GET /api/agent/briefing & reflection")

    # 11. Settings
    r = client.get("/api/settings")
    assert r.status_code == 200
    r = client.post("/api/settings", json={"notify_lead_minutes": "15"})
    assert r.status_code == 200
    print("[PASS] Settings GET/POST")

    print("\n===========================================")
    print("  ALL 11 AGENTIC SYSTEM TESTS PASSED 100%  ")
    print("===========================================")

if __name__ == "__main__":
    run_tests()