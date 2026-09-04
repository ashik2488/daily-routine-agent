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
        tomorrow_date = (date.today() + timedelta(days=1)).isoformat()
        completed = [t for t in tasks if t.get('status') == 'completed']
        pending = [t for t in tasks if t.get('status') != 'completed']
        pct = int((len(completed) / len(tasks)) * 100) if tasks else 0

        pending_str = ""
        if pending:
            pending_str = "\n\n📋 Unfinished tasks to rollover:\n" + "\n".join([f"• {t['title']}" for t in pending])

        msg = (
            f"🌙 Bedtime Routine Planning Time!\n\n"
            f"Today's Progress ({target_date}):\n"
            f"✅ Completed: {len(completed)}/{len(tasks)} tasks ({pct}%)\n"
            f"{pending_str}\n\n"
            f"⚡ Action Required: Open your Daily Routine Agent to log tomorrow's ({tomorrow_date}) plan before going to sleep!\n"
            f"🔗 http://127.0.0.1:8000"
        )

        return {
            "title": f"🌙 Bedtime Routine Planning ({tomorrow_date})",
            "message": msg,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "pending_tasks": [t['title'] for t in pending]
        }

    def decompose_task_into_subtasks(self, task_title: str, duration_minutes: int) -> List[Dict]:
        """
        Heuristic AI decomposition of a task into 3-5 actionable subtasks.
        Works completely offline — no external API needed.
        """
        title_lower = task_title.lower()

        # Pattern-based decomposition library
        patterns = [
            # Coding / Programming
            (r"\b(code|coding|develop|build|program|implement|feature|api|backend|frontend)\b",
             ["Define requirements & scope", "Design architecture / pseudocode",
              "Write core implementation", "Test and debug", "Review and document"]),
            # Study / Learning
            (r"\b(study|learn|course|lecture|module|tutorial|revision|exam|research)\b",
             ["Review previous notes", "Read / watch new material",
              "Take structured notes", "Solve practice problems", "Summarize key concepts"]),
            # Writing / Content
            (r"\b(write|essay|report|blog|article|draft|document|content|thesis)\b",
             ["Outline key points", "Write introduction & body draft",
              "Add supporting evidence / examples", "Edit for clarity and flow", "Final proofread"]),
            # Meeting / Presentation
            (r"\b(meeting|presentation|standup|call|pitch|demo|review)\b",
             ["Prepare agenda & talking points", "Gather relevant data / slides",
              "Send calendar invite (if needed)", "Conduct meeting / call", "Send summary & action items"]),
            # Workout / Fitness
            (r"\b(gym|workout|exercise|run|jog|train|yoga|stretch|fitness)\b",
             ["Warm-up (5-10 min)", "Main workout block", "Cool-down & stretching", "Hydrate and log progress"]),
            # Design / Creative
            (r"\b(design|ui|ux|wireframe|prototype|mockup|creative|graphic|visual)\b",
             ["Gather references & inspiration", "Sketch / wireframe concepts",
              "Create high-fidelity design", "Gather feedback", "Finalize and export assets"]),
            # Planning / Organization
            (r"\b(plan|organize|setup|configure|prepare|arrange|schedule)\b",
             ["List all required steps", "Prioritize and sequence items",
              "Set up environment / tools", "Execute planned steps", "Review and adjust"]),
            # Reading
            (r"\b(read|book|paper|article|chapter)\b",
             ["Set reading goal (pages / time)", "Active reading with highlights",
              "Note key insights", "Summarize main takeaways"]),
        ]

        selected_steps = None
        for pattern, steps in patterns:
            if re.search(pattern, title_lower):
                selected_steps = steps
                break

        # Generic fallback
        if not selected_steps:
            selected_steps = [
                f"Define goal for: {task_title}",
                "Gather required resources / materials",
                "Execute primary work block",
                "Review output and iterate",
                "Wrap up and document outcome"
            ]

        # Slice to fit duration — shorter tasks get fewer subtasks
        if duration_minutes <= 20:
            selected_steps = selected_steps[:2]
        elif duration_minutes <= 45:
            selected_steps = selected_steps[:3]
        elif duration_minutes <= 90:
            selected_steps = selected_steps[:4]

        # Distribute time proportionally
        n = len(selected_steps)
        base_min = max(5, duration_minutes // n)

        return [
            {"title": step, "estimated_minutes": base_min}
            for step in selected_steps
        ]

    def generate_weekly_analytics_report(self, days_data: list) -> str:
        """
        Generates a natural-language weekly summary from daily stats data.
        days_data: list of dicts with keys: date, total, completed, skipped
        """
        if not days_data:
            return "No data available for this week yet. Start logging your daily tasks to see your analytics!"

        total_tasks = sum(d.get("total", 0) for d in days_data)
        total_completed = sum(d.get("completed", 0) for d in days_data)
        total_skipped = sum(d.get("skipped", 0) for d in days_data)
        days_with_tasks = [d for d in days_data if d.get("total", 0) > 0]
        active_days = len(days_with_tasks)

        if total_tasks == 0:
            return "No tasks were logged this week. Use the Bedtime Task Ingestor each night to build your routine!"

        overall_pct = int((total_completed / total_tasks) * 100) if total_tasks else 0

        # Best day
        best_day = max(days_data, key=lambda d: (d.get("completed", 0) / d.get("total", 1) if d.get("total", 0) > 0 else 0))
        best_pct = int((best_day.get("completed", 0) / best_day.get("total", 1)) * 100) if best_day.get("total", 0) > 0 else 0

        # Consistency score
        consistency = int((active_days / 7) * 100)

        # Performance tier
        if overall_pct >= 80:
            tier = "Outstanding"
            emoji = "🏆"
            advice = "Exceptional discipline! Keep this momentum and consider stretching your goals."
        elif overall_pct >= 60:
            tier = "Strong"
            emoji = "🌟"
            advice = "Solid execution. Focus on your P1 tasks first each morning to push even higher."
        elif overall_pct >= 40:
            tier = "Building"
            emoji = "💪"
            advice = "You're building consistency. Try reducing your daily task count to improve completion rate."
        else:
            tier = "Getting Started"
            emoji = "🌱"
            advice = "Every expert was once a beginner. Pick 1-3 must-do tasks each day and build from there."

        report = (
            f"{emoji} **Weekly Performance: {tier}** ({overall_pct}% completion)\n\n"
            f"📋 Tasks Logged: {total_tasks} across {active_days}/7 active days\n"
            f"✅ Completed: {total_completed}  |  ✖ Skipped: {total_skipped}\n"
            f"📅 Consistency Score: {consistency}%\n"
            f"🏅 Best Day: {best_day.get('date', 'N/A')} ({best_pct}% completion)\n\n"
            f"💡 Agent Insight: {advice}"
        )
        return report


agent_instance = RoutineAgent()
