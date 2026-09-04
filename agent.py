import re
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import json
import requests
from database import get_tasks_for_date, update_task, get_settings

class RoutineAgent:
    def __init__(self):
        pass

    def parse_natural_language_tasks(self, raw_text: str, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses bedtime free-text task lists into structured task objects.
        """
        if not target_date:
            now = datetime.now()
            if now.hour >= 19:
                target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                target_date = now.strftime("%Y-%m-%d")

        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        parsed_tasks = []

        for line in lines:
            if line.endswith(":") and len(line) < 30 and not any(char.isdigit() for char in line):
                continue
            
            clean_line = re.sub(r"^(\*|\-|\d+[\.\)]|\u2022)\s*", "", line)
            if not clean_line:
                continue

            # 1. Detect Priority
            priority = "P2"
            if re.search(r"\b(p1|high|urgent|critical|important|🔥)\b", clean_line, re.IGNORECASE):
                priority = "P1"
            elif re.search(r"\b(p3|low|someday|optional)\b", clean_line, re.IGNORECASE):
                priority = "P3"

            # 2. Detect Energy Level
            energy_level = "Medium"
            if re.search(r"\b(deep work|focus|coding|study|hard|writing|gym|workout)\b", clean_line, re.IGNORECASE):
                energy_level = "High"
            elif re.search(r"\b(light|email|admin|organize|relax|read|walk)\b", clean_line, re.IGNORECASE):
                energy_level = "Low"

            # 3. Detect Category
            category = "Work"
            if re.search(r"\b(gym|workout|run|walk|meditate|sleep|breakfast|lunch|dinner|water|health|exercise)\b", clean_line, re.IGNORECASE):
                category = "Health"
            elif re.search(r"\b(study|course|read|learn|practice|research|tutorial|book)\b", clean_line, re.IGNORECASE):
                category = "Learning"
            elif re.search(r"\b(groceries|call|family|clean|chore|errand|shopping|personal)\b", clean_line, re.IGNORECASE):
                category = "Personal"
            elif re.search(r"\b(morning routine|night routine|wake up|brush|bath|bed)\b", clean_line, re.IGNORECASE):
                category = "Routine"

            # 4. Detect Duration
            duration = 30
            dur_match = re.search(r"(\d+)\s*(mins?|minutes?|hrs?|hours?)", clean_line, re.IGNORECASE)
            if dur_match:
                val = int(dur_match.group(1))
                unit = dur_match.group(2).lower()
                if "h" in unit:
                    duration = val * 60
                else:
                    duration = val

            # 5. Detect Start Time (Matches: 7:00 AM, 7am, 14:30, 9:00 PM, 9pm, at 8:00)
            start_time = None
            time_matches = list(re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", clean_line, re.IGNORECASE))
            
            for tm in time_matches:
                full_match = tm.group(0)
                h_str = tm.group(1)
                m_str = tm.group(2)
                meridiem = tm.group(3)
                
                # Check if this match is part of duration e.g. "30 mins" or "1 hour"
                prefix = clean_line[:tm.start()].strip().lower()
                suffix = clean_line[tm.end():].strip().lower()
                if suffix.startswith("min") or suffix.startswith("hr") or suffix.startswith("hour"):
                    continue

                h = int(h_str)
                m = int(m_str) if m_str else 0

                if meridiem:
                    meridiem = meridiem.lower()
                    if meridiem == "pm" and h < 12:
                        h += 12
                    elif meridiem == "am" and h == 12:
                        h = 0
                    start_time = f"{h:02d}:{m:02d}"
                    break
                elif m_str is not None and (0 <= h <= 23 and 0 <= m <= 59):
                    start_time = f"{h:02d}:{m:02d}"
                    break
                elif "at " in prefix[-5:] and 0 <= h <= 23:
                    start_time = f"{h:02d}:00"
                    break

            # 6. Extract clean Title
            title = clean_line
            title = re.sub(r"\[(P1|P2|P3|High|Medium|Low)\]", "", title, flags=re.IGNORECASE)
            title = re.sub(r"#(work|health|learning|personal|routine)", "", title, flags=re.IGNORECASE)
            title = re.sub(r"\s+", " ", title).strip()

            parsed_tasks.append({
                "title": title,
                "description": f"Scheduled for {target_date}",
                "task_date": target_date,
                "start_time": start_time,
                "duration_minutes": duration,
                "priority": priority,
                "energy_level": energy_level,
                "category": category,
                "is_mit": (priority == "P1"),
                "status": "pending"
            })

        return parsed_tasks

    def optimize_schedule(self, task_date: str) -> Dict[str, Any]:
        tasks = get_tasks_for_date(task_date)
        if not tasks:
            return {
                "status": "empty",
                "message": f"No tasks found for {task_date} to optimize.",
                "tasks": [],
                "agent_advice": "No tasks logged yet. Add your tasks for tonight to generate your daily plan!"
            }

        fixed_tasks = [t for t in tasks if t.get('start_time')]
        flexible_tasks = [t for t in tasks if not t.get('start_time')]

        priority_weights = {"P1": 0, "P2": 1, "P3": 2}
        energy_weights = {"High": 0, "Medium": 1, "Low": 2}
        flexible_tasks.sort(key=lambda t: (priority_weights.get(t['priority'], 1), energy_weights.get(t['energy_level'], 1)))

        occupied_slots = set()
        for t in fixed_tasks:
            occupied_slots.add(t['start_time'][:2])

        available_hours = [
            "08:00", "09:00", "10:00", "11:00",
            "14:00", "15:00", "16:00", "17:00",
            "19:00", "20:00", "21:00"
        ]

        slot_idx = 0
        updated_count = 0
        for t in flexible_tasks:
            while slot_idx < len(available_hours) and available_hours[slot_idx][:2] in occupied_slots:
                slot_idx += 1
            
            if slot_idx < len(available_hours):
                chosen_time = available_hours[slot_idx]
                update_task(t['id'], {'start_time': chosen_time})
                occupied_slots.add(chosen_time[:2])
                slot_idx += 1
                updated_count += 1

        all_tasks = get_tasks_for_date(task_date)
        
        mit_count = 0
        for t in all_tasks:
            if t.get('priority') == 'P1' and mit_count < 3:
                update_task(t['id'], {'is_mit': 1})
                mit_count += 1
            elif mit_count < 3 and t.get('energy_level') == 'High':
                update_task(t['id'], {'is_mit': 1})
                mit_count += 1
            else:
                update_task(t['id'], {'is_mit': 0})

        final_tasks = get_tasks_for_date(task_date)
        
        total_duration = sum(t.get('duration_minutes', 30) for t in final_tasks)
        total_hours = round(total_duration / 60, 1)
        mits = [t['title'] for t in final_tasks if t.get('is_mit')]

        advice_lines = []
        advice_lines.append(f"🎯 **Target Workload**: {total_hours} hours across {len(final_tasks)} planned tasks.")
        if mits:
            advice_lines.append(f"⭐ **Top Priorities (MITs)**: {', '.join(mits)}.")
        if total_hours > 8.5:
            advice_lines.append("⚠️ **High Workload Notice**: You have over 8.5 hours scheduled. Take 10-minute restorative breaks between focus blocks.")
        else:
            advice_lines.append("✨ **Balanced Schedule**: Your day has healthy breathing room between high-focus blocks and restorative intervals.")

        advice_summary = "\n".join(advice_lines)

        return {
            "status": "success",
            "message": f"Schedule optimized successfully! {updated_count} flexible tasks assigned optimal time slots.",
            "tasks": final_tasks,
            "agent_advice": advice_summary,
            "mits": mits,
            "total_hours": total_hours
        }

    def generate_morning_briefing(self, target_date: str) -> Dict[str, Any]:
        tasks = get_tasks_for_date(target_date)
        if not tasks:
            return {
                "title": "🌅 Good Morning! Plan Your Day",
                "message": "You have no tasks scheduled yet for today. Open your Routine Agent to log your plan.",
                "task_count": 0
            }

        mits = [t for t in tasks if t.get('is_mit')]
        first_task = next((t for t in tasks if t.get('start_time')), tasks[0])
        
        msg_parts = [
            f"You have {len(tasks)} tasks scheduled for today.",
        ]
        if mits:
            msg_parts.append(f"Top Priority: {mits[0]['title']}")
        if first_task and first_task.get('start_time'):
            msg_parts.append(f"First up: '{first_task['title']}' at {first_task['start_time']}.")

        return {
            "title": f"🌅 Morning Briefing ({target_date})",
            "message": " | ".join(msg_parts),
            "task_count": len(tasks),
            "mits": [t['title'] for t in mits]
        }

    def generate_evening_reflection(self, target_date: str) -> Dict[str, Any]:
        tasks = get_tasks_for_date(target_date)
        if not tasks:
            return {
                "title": "🌙 Night Routine Planning Time",
                "message": "Time to reflect on your day and add your tasks for tomorrow before sleep.",
                "pending_tasks": []
            }

        completed = [t for t in tasks if t.get('status') == 'completed']
        pending = [t for t in tasks if t.get('status') != 'completed']
        pct = int((len(completed) / len(tasks)) * 100) if tasks else 0

        return {
            "title": "🌙 Evening Reflection & Night Planning",
            "message": f"You completed {len(completed)}/{len(tasks)} tasks today ({pct}%). Time to log tomorrow's routine!",
            "completed_count": len(completed),
            "pending_count": len(pending),
            "pending_tasks": [t['title'] for t in pending]
        }

agent_instance = RoutineAgent()
