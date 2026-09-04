from fastapi.testclient import TestClient
from app import app
import sys

# UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

client = TestClient(app)

def run_tests():
    print("Running integration tests...")
    
    # 1. Root dashboard
    r = client.get("/")
    assert r.status_code == 200
    print("[PASS] GET / (Dashboard HTML)")

    # 2. Add task
    r = client.post("/api/tasks", json={
        "title": "Evening Test Task",
        "task_date": "2026-09-06",
        "start_time": "19:00",
        "duration_minutes": 45,
        "priority": "P1",
        "category": "Work"
    })
    assert r.status_code == 200
    task_id = r.json()["id"]
    print(f"[PASS] POST /api/tasks (Created task #{task_id})")

    # 3. Bulk Night Entry
    r = client.post("/api/tasks/bulk-night-entry", json={
        "raw_text": "- Wake up at 6:30 AM #routine\n- Morning Run for 30 mins [P1]\n- Deep Work 10am for 2 hrs",
        "target_date": "2026-09-06"
    })
    assert r.status_code == 200
    print(f"[PASS] POST /api/tasks/bulk-night-entry (Created {r.json()['tasks_created']} tasks)")

    # 4. List tasks
    r = client.get("/api/tasks?date=2026-09-06")
    assert r.status_code == 200
    print(f"[PASS] GET /api/tasks (Found {len(r.json()['tasks'])} tasks)")

    # 5. Optimize routine
    r = client.post("/api/agent/optimize", json={"date": "2026-09-06"})
    assert r.status_code == 200
    print("[PASS] POST /api/agent/optimize")

    # 6. Briefing & Reflection
    r = client.get("/api/agent/briefing?date=2026-09-06")
    assert r.status_code == 200
    r = client.get("/api/agent/reflection?date=2026-09-06")
    assert r.status_code == 200
    print("[PASS] GET /api/agent/briefing & reflection")

    # 7. Settings
    r = client.get("/api/settings")
    assert r.status_code == 200
    r = client.post("/api/settings", json={"notify_lead_minutes": "15"})
    assert r.status_code == 200
    print("[PASS] Settings GET/POST")

    print("\n===========================================")
    print("  ALL 7 AGENTIC SYSTEM TESTS PASSED 100%   ")
    print("===========================================")

if __name__ == "__main__":
    run_tests()