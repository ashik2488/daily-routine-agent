import sys
import argparse
from datetime import datetime, date, timedelta

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from database import init_db, create_task, get_tasks_for_date, update_task
from agent import agent_instance
from notifier import notify

def main():
    init_db()
    parser = argparse.ArgumentParser(description="Daily Routine Agent CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("--date", default=date.today().isoformat(), help="Task date (YYYY-MM-DD)")
    add_parser.add_argument("--time", help="Start time (HH:MM)")
    add_parser.add_argument("--duration", type=int, default=30, help="Duration in minutes")
    add_parser.add_argument("--priority", default="P2", choices=["P1", "P2", "P3"], help="Priority")

    # Bedtime dump
    dump_parser = subparsers.add_parser("dump", help="Parse and log bedtime tasks from text")
    dump_parser.add_argument("text", help="Bedtime free-text task list")
    dump_parser.add_argument("--date", help="Target date (default: tomorrow)")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks for date")
    list_parser.add_argument("--date", default=date.today().isoformat(), help="Date (YYYY-MM-DD)")

    # Optimize
    opt_parser = subparsers.add_parser("optimize", help="Run AI schedule optimization")
    opt_parser.add_argument("--date", default=date.today().isoformat(), help="Date (YYYY-MM-DD)")

    # Test notify
    subparsers.add_parser("test-notify", help="Dispatch a test Windows toast notification")

    args = parser.parse_args()

    if args.command == "add":
        task_id = create_task({
            "title": args.title,
            "task_date": args.date,
            "start_time": args.time,
            "duration_minutes": args.duration,
            "priority": args.priority,
            "is_mit": (args.priority == "P1")
        })
        print(f"[OK] Created Task #{task_id}: {args.title} on {args.date}")

    elif args.command == "dump":
        tasks = agent_instance.parse_natural_language_tasks(args.text, args.date)
        for t in tasks:
            create_task(t)
        print(f"[OK] Successfully parsed & logged {len(tasks)} bedtime tasks!")

    elif args.command == "list":
        tasks = get_tasks_for_date(args.date)
        print(f"\nTasks for {args.date} ({len(tasks)} total):")
        print("-" * 60)
        for t in tasks:
            status_icon = "[DONE]" if t['status'] == 'completed' else "[TODO]"
            mit_str = "*[MIT] " if t['is_mit'] else ""
            time_str = f"at {t['start_time']}" if t['start_time'] else "(flexible)"
            print(f"{status_icon} [{t['priority']}] #{t['id']} {mit_str}{t['title']} {time_str} ({t['duration_minutes']}m)")
        print("-" * 60)

    elif args.command == "optimize":
        res = agent_instance.optimize_schedule(args.date)
        print("\n" + res['agent_advice'])

    elif args.command == "test-notify":
        notify("Daily Routine Agent Test", "Test alert dispatched successfully to your desktop!")
        print("[OK] Test notification dispatched.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
