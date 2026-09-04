// ─── State ───────────────────────────────────────────────────────────────────
let currentDate = new Date().toISOString().split("T")[0];
let currentTasks = [];
let pomodoroInterval = null;
let pomodoroSecondsLeft = 25 * 60;
let pomodoroRunning = false;
let pomodoroAudioCtx = null;
let pomodoroAudioNode = null;
let expandedSubtasks = {}; // taskId → bool

// ─── DOM Elements ─────────────────────────────────────────────────────────────
const liveClock = document.getElementById("liveClock");
const selectedDateInput = document.getElementById("selectedDateInput");
const taskListContainer = document.getElementById("taskListContainer");
const aiAdviceBox = document.getElementById("aiAdviceBox");
const aiAdviceContent = document.getElementById("aiAdviceContent");
const statTotal = document.getElementById("statTotal");
const statCompleted = document.getElementById("statCompleted");
const statPercent = document.getElementById("statPercent");
const statMits = document.getElementById("statMits");
const statHours = document.getElementById("statHours");
const statProgressBar = document.getElementById("statProgressBar");

// ─── Clock ────────────────────────────────────────────────────────────────────
function updateClock() { liveClock.textContent = new Date().toLocaleTimeString(); }
setInterval(updateClock, 1000); updateClock();

// ─── Tab Switcher ─────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
    btn.classList.add("active");
    const tabId = btn.dataset.tab;
    const el = document.getElementById(tabId);
    if (el) el.style.display = "block";
    if (tabId === "briefingTab") loadBriefings();
    else if (tabId === "settingsTab") loadSettings();
    else if (tabId === "habitsTab") loadHabits();
    else if (tabId === "analyticsTab") loadAnalytics();
  });
});

// ─── Date Navigation ──────────────────────────────────────────────────────────
selectedDateInput.value = currentDate;
document.getElementById("nightTargetDate").value = getTomorrowDate();
function getTomorrowDate() {
  const d = new Date(); d.setDate(d.getDate() + 1); return d.toISOString().split("T")[0];
}
selectedDateInput.addEventListener("change", e => { currentDate = e.target.value; loadTasks(); });
document.getElementById("prevDayBtn").addEventListener("click", () => {
  const d = new Date(currentDate); d.setDate(d.getDate() - 1);
  currentDate = d.toISOString().split("T")[0]; selectedDateInput.value = currentDate; loadTasks();
});
document.getElementById("nextDayBtn").addEventListener("click", () => {
  const d = new Date(currentDate); d.setDate(d.getDate() + 1);
  currentDate = d.toISOString().split("T")[0]; selectedDateInput.value = currentDate; loadTasks();
});
document.getElementById("todayBtn").addEventListener("click", () => {
  currentDate = new Date().toISOString().split("T")[0];
  selectedDateInput.value = currentDate; loadTasks();
});

// ─── Load Tasks ───────────────────────────────────────────────────────────────
async function loadTasks() {
  try {
    taskListContainer.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:2rem;">Loading tasks...</div>`;
    const res = await fetch(`/api/tasks?date=${currentDate}`);
    const data = await res.json();
    currentTasks = data.tasks || [];
    renderTasks();
    updateStats();
  } catch (err) {
    taskListContainer.innerHTML = `<div style="color:var(--accent-rose);padding:1rem;">Failed to load: ${err.message}</div>`;
  }
}

// ─── Render Tasks with Subtask Accordion ──────────────────────────────────────
function renderTasks() {
  if (currentTasks.length === 0) {
    taskListContainer.innerHTML = `
      <div style="text-align:center;padding:3rem 1rem;color:var(--text-muted);">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">🌙</div>
        <p style="font-weight:600;color:var(--text-secondary);">No tasks scheduled for this date.</p>
        <p style="font-size:0.85rem;margin-top:0.25rem;">Use the <strong>Night Ingestor</strong> tab or click <strong>+ Add Task</strong>.</p>
      </div>`;
    return;
  }
  taskListContainer.innerHTML = currentTasks.map(t => renderTaskHTML(t)).join("");
}

function renderTaskHTML(t) {
  const isCompleted = t.status === "completed";
  const isSkipped = t.status === "skipped";
  const priorityClass = `badge-${t.priority.toLowerCase()}`;
  const timeDisplay = t.start_time ? `🕒 ${t.start_time}` : "⏳ Flexible";
  const mitBadge = t.is_mit ? `<span class="badge badge-mit">⭐ MIT</span>` : "";
  let statusBadge = "";
  if (isCompleted) statusBadge = `<span class="badge badge-status-done">✔ Done</span>`;
  else if (isSkipped) statusBadge = `<span class="badge badge-status-skip">✖ Skipped</span>`;

  const subtaskSection = expandedSubtasks[t.id]
    ? `<div class="subtask-panel" id="subtaskPanel-${t.id}">
         <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Loading subtasks...</div>
       </div>`
    : "";

  return `
    <div class="task-item ${isCompleted ? 'completed' : ''} ${isSkipped ? 'skipped' : ''}" data-id="${t.id}">
      <div class="task-left">
        <div class="status-buttons">
          <button type="button" class="btn-status btn-status-check ${isCompleted ? 'active' : ''}"
            onclick="setTaskStatus(${t.id}, 'completed')" title="Mark Completed">✔</button>
          <button type="button" class="btn-status btn-status-cross ${isSkipped ? 'active' : ''}"
            onclick="setTaskStatus(${t.id}, 'skipped')" title="Mark Skipped">✖</button>
        </div>
        <div class="task-content">
          <div class="task-text">${escapeHtml(t.title)}</div>
          <div class="task-meta">
            <span>${timeDisplay}</span><span>•</span>
            <span>${t.duration_minutes || 30}m</span><span>•</span>
            <span class="badge ${priorityClass}">${t.priority}</span>
            <span class="badge badge-cat">${t.category || 'Work'}</span>
            ${mitBadge}${statusBadge}
          </div>
          ${subtaskSection}
        </div>
      </div>
      <div class="task-actions">
        <button class="icon-btn" onclick="toggleSubtasks(${t.id})" title="Show subtasks">📝</button>
        <button class="icon-btn" onclick="aiDecompose(${t.id})" title="AI Break Down">⚡</button>
        <button class="icon-btn" onclick="openEditModal(${t.id})" title="Edit">✏️</button>
        <button class="icon-btn icon-btn-delete" onclick="deleteTaskItem(${t.id})" title="Delete">🗑️</button>
      </div>
    </div>`;
}

// ─── Subtask Accordion ────────────────────────────────────────────────────────
async function toggleSubtasks(taskId) {
  expandedSubtasks[taskId] = !expandedSubtasks[taskId];
  renderTasks();
  if (expandedSubtasks[taskId]) await refreshSubtaskPanel(taskId);
}

async function refreshSubtaskPanel(taskId) {
  const panel = document.getElementById(`subtaskPanel-${taskId}`);
  if (!panel) return;
  try {
    const res = await fetch(`/api/tasks/${taskId}/subtasks`);
    const data = await res.json();
    const subtasks = data.subtasks || [];
    if (subtasks.length === 0) {
      panel.innerHTML = `
        <div style="color:var(--text-muted);font-size:0.8rem;padding:0.4rem 0;">
          No subtasks yet. Click ⚡ for AI breakdown.
        </div>
        <div style="margin-top:0.5rem;">${addSubtaskForm(taskId)}</div>`;
    } else {
      panel.innerHTML = subtasks.map(st => `
        <div class="subtask-row ${st.is_completed ? 'subtask-done' : ''}">
          <button class="subtask-check ${st.is_completed ? 'active' : ''}"
            onclick="toggleSubtask(${st.id}, ${taskId})">
            ${st.is_completed ? '✔' : '○'}
          </button>
          <span class="subtask-title">${escapeHtml(st.title)}</span>
          <span class="subtask-mins">${st.estimated_minutes || 15}m</span>
          <button class="icon-btn icon-btn-delete" style="font-size:0.75rem;"
            onclick="removeSubtask(${st.id}, ${taskId})">🗑</button>
        </div>`).join("") +
        `<div style="margin-top:0.5rem;">${addSubtaskForm(taskId)}</div>`;
    }
  } catch (e) {
    panel.innerHTML = `<div style="color:var(--accent-rose);font-size:0.8rem;">Error loading subtasks</div>`;
  }
}

function addSubtaskForm(taskId) {
  return `<div style="display:flex;gap:0.5rem;margin-top:0.4rem;">
    <input type="text" class="form-control" placeholder="Add subtask..." id="newSubtask-${taskId}"
      style="flex:1;font-size:0.8rem;padding:0.3rem 0.6rem;" onkeydown="if(event.key==='Enter'){addSubtask(${taskId});event.preventDefault();}">
    <button class="btn btn-emerald btn-sm" onclick="addSubtask(${taskId})">+</button>
  </div>`;
}

async function addSubtask(taskId) {
  const input = document.getElementById(`newSubtask-${taskId}`);
  if (!input || !input.value.trim()) return;
  await fetch("/api/subtasks", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ task_id: taskId, title: input.value.trim(), estimated_minutes: 15 })
  });
  input.value = "";
  await refreshSubtaskPanel(taskId);
}

async function toggleSubtask(subtaskId, taskId) {
  await fetch(`/api/subtasks/${subtaskId}/toggle`, { method: "PUT" });
  await refreshSubtaskPanel(taskId);
}

async function removeSubtask(subtaskId, taskId) {
  await fetch(`/api/subtasks/${subtaskId}`, { method: "DELETE" });
  await refreshSubtaskPanel(taskId);
}

async function aiDecompose(taskId) {
  const task = currentTasks.find(t => t.id === taskId);
  if (!task) return;
  if (!confirm(`⚡ AI will generate subtasks for:\n"${task.title}"\n\nAny existing subtasks will be kept. Continue?`)) return;

  expandedSubtasks[taskId] = true;
  renderTasks();
  const panel = document.getElementById(`subtaskPanel-${taskId}`);
  if (panel) panel.innerHTML = `<div style="color:#818cf8;font-size:0.8rem;">⚡ Generating AI subtasks...</div>`;

  try {
    const res = await fetch(`/api/tasks/${taskId}/ai-decompose`, { method: "POST" });
    const data = await res.json();
    await refreshSubtaskPanel(taskId);
    showToast(`✅ Generated ${data.subtasks?.length || 0} subtasks for "${task.title}"`);
  } catch (e) {
    showToast("❌ AI decompose failed: " + e.message, "error");
  }
}

// ─── Stats ────────────────────────────────────────────────────────────────────
function updateStats() {
  const total = currentTasks.length;
  const completed = currentTasks.filter(t => t.status === "completed").length;
  const mits = currentTasks.filter(t => t.is_mit && t.status !== "completed").length;
  const totalMins = currentTasks.reduce((acc, t) => acc + (t.duration_minutes || 30), 0);
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  statTotal.textContent = total;
  statCompleted.textContent = completed;
  statPercent.textContent = `${percent}% finished`;
  statMits.textContent = mits;
  statHours.textContent = `${(totalMins / 60).toFixed(1)}h`;
  statProgressBar.style.width = `${percent}%`;
}

// ─── Task Status Toggle ───────────────────────────────────────────────────────
async function setTaskStatus(taskId, targetStatus) {
  const task = currentTasks.find(t => t.id === taskId);
  if (!task) return;
  const newStatus = task.status === targetStatus ? "pending" : targetStatus;
  try {
    await fetch(`/api/tasks/${taskId}`, {
      method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ status: newStatus })
    });
    task.status = newStatus;
    renderTasks();
    updateStats();
    if (expandedSubtasks[taskId]) await refreshSubtaskPanel(taskId);
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

// ─── Delete Task ──────────────────────────────────────────────────────────────
async function deleteTaskItem(taskId) {
  if (!confirm("Delete this task?")) return;
  try {
    await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
    currentTasks = currentTasks.filter(t => t.id !== taskId);
    delete expandedSubtasks[taskId];
    renderTasks(); updateStats();
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

// ─── AI Optimize ─────────────────────────────────────────────────────────────
document.getElementById("optimizeScheduleBtn").addEventListener("click", async () => {
  const btn = document.getElementById("optimizeScheduleBtn");
  btn.disabled = true; btn.textContent = "✨ Optimizing...";
  try {
    const res = await fetch("/api/agent/optimize", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ date: currentDate })
    });
    const data = await res.json();
    if (data.status === "success") {
      aiAdviceBox.style.display = "block";
      aiAdviceContent.textContent = data.agent_advice || data.message;
      loadTasks();
    } else { showToast(data.message || "Optimization finished."); }
  } catch (err) { showToast("Optimization error: " + err.message, "error"); }
  finally { btn.disabled = false; btn.textContent = "✨ AI Optimize"; }
});

// ─── Night Ingestor ───────────────────────────────────────────────────────────
document.getElementById("submitNightTasksBtn").addEventListener("click", async () => {
  const rawText = document.getElementById("nightTextInput").value.trim();
  const targetDate = document.getElementById("nightTargetDate").value;
  if (!rawText) { showToast("Please enter some tasks first."); return; }
  const btn = document.getElementById("submitNightTasksBtn");
  btn.disabled = true; btn.textContent = "⏳ Parsing...";
  try {
    const res = await fetch("/api/tasks/bulk-night-entry", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ raw_text: rawText, target_date: targetDate })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`🎉 Scheduled ${data.tasks_created} tasks for ${data.target_date}!`);
      document.getElementById("nightTextInput").value = "";
      await fetch("/api/agent/optimize", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ date: targetDate })
      });
      currentDate = targetDate;
      selectedDateInput.value = currentDate;
      document.querySelector('[data-tab="scheduleTab"]').click();
      loadTasks();
    }
  } catch (err) { showToast("Error: " + err.message, "error"); }
  finally { btn.disabled = false; btn.textContent = "🚀 Parse, Schedule & Notify"; }
});

// ─── Voice Input ──────────────────────────────────────────────────────────────
document.getElementById("voiceMicBtn").addEventListener("click", () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { showToast("Voice input not supported in this browser."); return; }
  const rec = new SpeechRecognition();
  rec.lang = "en-US"; rec.continuous = false; rec.interimResults = false;
  const statusEl = document.getElementById("voiceStatus");
  const textarea = document.getElementById("nightTextInput");
  statusEl.style.display = "block";
  rec.start();
  rec.onresult = e => {
    const text = e.results[0][0].transcript;
    textarea.value = (textarea.value ? textarea.value + "\n" : "") + "- " + text;
    statusEl.style.display = "none";
  };
  rec.onerror = () => { statusEl.style.display = "none"; showToast("Voice recognition failed. Try again."); };
  rec.onend = () => { statusEl.style.display = "none"; };
});

// ─── Templates ────────────────────────────────────────────────────────────────
function applyTemplate(type) {
  const ta = document.getElementById("nightTextInput");
  if (type === "productive") {
    ta.value = `- Wake up at 7:00 AM #routine
- 30 mins Morning Stretch & Coffee [Health]
- Deep Work on Project Architecture at 9:00 AM for 2 hours [P1] [High]
- Team Standup Meeting at 11:30 AM for 30 mins #work
- Healthy Lunch & Walk at 1:00 PM
- Client Sprint Review at 2:30 PM [P1]
- Code Review & Admin Inbox at 4:30 PM [Low]
- Evening Gym Workout at 6:30 PM for 1 hour [P2]
- Dinner & Book Reading at 8:30 PM
- Night Routine & Bed at 10:30 PM`;
  } else if (type === "fitness") {
    ta.value = `- Wake up at 6:30 AM & Hydrate
- 5km Morning Run & Workout at 7:00 AM for 1 hour [High] [P1]
- High Protein Breakfast at 8:30 AM
- Deep Focus Work Block at 10:00 AM for 3 hours [P1]
- Afternoon Mobility & Stretch at 3:00 PM for 20 mins
- Evening Walk in nature at 6:00 PM
- Healthy Meal Prep at 7:30 PM
- Foam Roll & Sleep at 10:00 PM`;
  } else if (type === "study") {
    ta.value = `- Wake up at 7:30 AM #routine
- Algorithm & Coding Practice at 8:30 AM for 90 mins [P1] [High]
- Research Paper Reading at 11:00 AM for 1 hour [P2]
- Break & Lunch at 12:30 PM
- System Design Course Module at 2:00 PM for 2 hours [P1]
- Flashcards & Note Review at 5:00 PM for 45 mins
- Evening Relaxation & Walk at 7:00 PM
- Sleep at 11:00 PM`;
  }
}

// ─── Habits Tab ───────────────────────────────────────────────────────────────
async function loadHabits() {
  const today = new Date().toISOString().split("T")[0];
  const grid = document.getElementById("habitsGrid");
  grid.innerHTML = `<div style="color:var(--text-muted);padding:1rem;">Loading...</div>`;
  try {
    const res = await fetch(`/api/habits?date=${today}`);
    const data = await res.json();
    const habits = data.habits || [];
    if (habits.length === 0) {
      grid.innerHTML = `<div style="color:var(--text-muted);padding:2rem;text-align:center;">
        No habits yet. Click <strong>+ New Habit</strong> to get started!</div>`;
      return;
    }
    grid.innerHTML = habits.map(h => `
      <div class="habit-card ${h.today_done ? 'habit-done' : ''}" onclick="toggleHabit(${h.id})">
        <div class="habit-icon">${h.icon || '⭐'}</div>
        <div class="habit-title">${escapeHtml(h.title)}</div>
        <div class="habit-streak">🔥 ${h.streak_count || 0} day streak</div>
        <div class="habit-check">${h.today_done ? '✔ Done' : 'Tap to complete'}</div>
        <button class="icon-btn icon-btn-delete habit-delete-btn" onclick="deleteHabit(event,${h.id})"
          title="Delete habit">🗑</button>
      </div>`).join("");
  } catch (e) { grid.innerHTML = `<div style="color:var(--accent-rose);">Error loading habits</div>`; }
}

async function toggleHabit(habitId) {
  const today = new Date().toISOString().split("T")[0];
  await fetch(`/api/habits/${habitId}/toggle?date=${today}`, { method: "POST" });
  loadHabits();
}

async function deleteHabit(event, habitId) {
  event.stopPropagation();
  if (!confirm("Delete this habit and all its logs?")) return;
  await fetch(`/api/habits/${habitId}`, { method: "DELETE" });
  loadHabits();
}

document.getElementById("openAddHabitBtn").addEventListener("click", () => {
  document.getElementById("habitModal").style.display = "flex";
  document.getElementById("habitTitle").value = "";
  document.getElementById("habitIcon").value = "⭐";
});
document.getElementById("closeHabitModalBtn").addEventListener("click", () => {
  document.getElementById("habitModal").style.display = "none";
});
document.getElementById("habitForm").addEventListener("submit", async e => {
  e.preventDefault();
  const payload = {
    title: document.getElementById("habitTitle").value.trim(),
    icon: document.getElementById("habitIcon").value.trim() || "⭐",
    frequency: document.getElementById("habitFrequency").value
  };
  await fetch("/api/habits", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  document.getElementById("habitModal").style.display = "none";
  loadHabits();
});

// ─── Analytics Tab ────────────────────────────────────────────────────────────
async function loadAnalytics() {
  try {
    const res = await fetch("/api/analytics/weekly");
    const data = await res.json();
    const days = data.days || [];
    // Render report
    const reportEl = document.getElementById("analyticsReport");
    if (reportEl) {
      const md = (data.report || "No data yet.").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      reportEl.innerHTML = md;
    }
    // Draw chart
    drawAnalyticsChart(days);
  } catch (e) {
    const reportEl = document.getElementById("analyticsReport");
    if (reportEl) reportEl.textContent = "Error loading analytics.";
  }
}

function drawAnalyticsChart(days) {
  const canvas = document.getElementById("analyticsChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.parentElement.clientWidth || 400;
  const H = 180;
  canvas.width = W * dpr; canvas.height = H * dpr;
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  if (!days || days.length === 0) {
    ctx.fillStyle = "#64748b";
    ctx.font = "14px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("No data yet — start logging tasks!", W / 2, H / 2);
    return;
  }

  const padL = 10, padR = 10, padB = 32, padT = 10;
  const chartW = W - padL - padR;
  const chartH = H - padB - padT;
  const n = days.length;
  const barW = Math.max(8, (chartW / n) * 0.55);
  const gap = chartW / n;

  const maxTotal = Math.max(...days.map(d => d.total || 0), 1);

  days.forEach((d, i) => {
    const x = padL + i * gap + gap / 2;
    const total = d.total || 0;
    const completed = d.completed || 0;
    const totalH = total > 0 ? (total / maxTotal) * chartH : 0;
    const doneH = total > 0 ? (completed / maxTotal) * chartH : 0;

    // Background bar
    ctx.fillStyle = "rgba(51,65,85,0.6)";
    ctx.beginPath(); ctx.roundRect(x - barW / 2, padT + (chartH - totalH), barW, totalH, 4);
    ctx.fill();

    // Completed bar
    const grad = ctx.createLinearGradient(0, padT, 0, padT + chartH);
    grad.addColorStop(0, "#10b981"); grad.addColorStop(1, "#06b6d4");
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.roundRect(x - barW / 2, padT + (chartH - doneH), barW, doneH, 4);
    ctx.fill();

    // Label
    ctx.fillStyle = "#64748b"; ctx.font = "10px system-ui"; ctx.textAlign = "center";
    const label = d.date ? d.date.slice(5) : "";
    ctx.fillText(label, x, H - 6);
    if (total > 0) {
      ctx.fillStyle = "#e2e8f0"; ctx.font = "bold 10px system-ui";
      ctx.fillText(completed + "/" + total, x, padT + (chartH - totalH) - 4);
    }
  });
}

// ─── Briefings ────────────────────────────────────────────────────────────────
async function loadBriefings() {
  try {
    const morningRes = await fetch(`/api/agent/briefing?date=${currentDate}`);
    const m = await morningRes.json();
    document.getElementById("morningDigestBox").innerHTML = `
      <h4 style="color:#fbbf24;margin-bottom:0.5rem;">${m.title}</h4>
      <p style="color:#f1f5f9;font-size:0.95rem;">${m.message}</p>
      <div style="margin-top:0.8rem;font-size:0.85rem;color:var(--text-secondary);">
        <strong>Planned Tasks:</strong> ${m.task_count || 0}
      </div>`;
    const eveningRes = await fetch(`/api/agent/reflection?date=${currentDate}`);
    const ev = await eveningRes.json();
    document.getElementById("eveningDigestBox").innerHTML = `
      <h4 style="color:#c084fc;margin-bottom:0.5rem;">${ev.title}</h4>
      <p style="color:#f1f5f9;font-size:0.95rem;">${ev.message}</p>
      ${ev.pending_tasks && ev.pending_tasks.length > 0
        ? `<div style="margin-top:0.8rem;font-size:0.85rem;color:#fb7185;">
             <strong>Unfinished:</strong> ${ev.pending_tasks.join(", ")}</div>`
        : `<div style="margin-top:0.8rem;font-size:0.85rem;color:#10b981;">🎉 All tasks wrapped up!</div>`}`;
  } catch (err) { console.error("Briefings load error:", err); }
}

// ─── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ""; };
    set("set_email_recipient", data.email_recipient);
    set("set_email_sender", data.email_sender);
    set("set_email_smtp_password", data.email_smtp_password);
    set("set_enable_email_notifications", data.enable_email_notifications || "true");
    set("set_email_smtp_host", data.email_smtp_host || "smtp.gmail.com");
    set("set_email_smtp_port", data.email_smtp_port || "587");
    set("set_morning_briefing_time", data.morning_briefing_time || "07:30");
    set("set_evening_planning_time", data.evening_planning_time || "22:00");
    set("set_notify_lead_minutes", data.notify_lead_minutes || "10");
    set("set_enable_audio_chime", data.enable_audio_chime || "true");
    set("set_discord_webhook_url", data.discord_webhook_url);
    set("set_telegram_bot_token", data.telegram_bot_token);
    set("set_telegram_chat_id", data.telegram_chat_id);
  } catch (err) { console.error("Settings load error:", err); }
}

document.getElementById("settingsForm").addEventListener("submit", async e => {
  e.preventDefault();
  const get = id => document.getElementById(id)?.value || "";
  const payload = {
    email_recipient: get("set_email_recipient"),
    email_sender: get("set_email_sender"),
    email_smtp_password: get("set_email_smtp_password"),
    enable_email_notifications: get("set_enable_email_notifications"),
    email_smtp_host: get("set_email_smtp_host"),
    email_smtp_port: get("set_email_smtp_port"),
    morning_briefing_time: get("set_morning_briefing_time"),
    evening_planning_time: get("set_evening_planning_time"),
    notify_lead_minutes: get("set_notify_lead_minutes"),
    enable_audio_chime: get("set_enable_audio_chime"),
    discord_webhook_url: get("set_discord_webhook_url"),
    telegram_bot_token: get("set_telegram_bot_token"),
    telegram_chat_id: get("set_telegram_chat_id")
  };
  await fetch("/api/settings", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  showToast("✅ Settings saved!");
});

// ─── Test Email ───────────────────────────────────────────────────────────────
async function triggerTestEmail() {
  const recipient = document.getElementById("set_email_recipient")?.value;
  if (!recipient) { showToast("Please enter a recipient email first.", "error"); return; }
  const payload = {
    email_recipient: recipient,
    email_sender: document.getElementById("set_email_sender")?.value,
    email_smtp_password: document.getElementById("set_email_smtp_password")?.value,
    enable_email_notifications: document.getElementById("set_enable_email_notifications")?.value,
    email_smtp_host: document.getElementById("set_email_smtp_host")?.value,
    email_smtp_port: document.getElementById("set_email_smtp_port")?.value
  };
  await fetch("/api/settings", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  try {
    const res = await fetch("/api/notifications/test-email", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ recipient }) });
    const data = await res.json();
    showToast(res.ok ? "📧 " + data.message : "❌ " + data.detail, res.ok ? "success" : "error");
  } catch (err) { showToast("Error: " + err.message, "error"); }
}
document.getElementById("testEmailBtn").addEventListener("click", triggerTestEmail);
document.getElementById("quickTestEmailBtn").addEventListener("click", () => {
  document.querySelector('[data-tab="settingsTab"]').click(); triggerTestEmail();
});

// ─── Test Windows Notification ────────────────────────────────────────────────
document.getElementById("testNotifyBtn").addEventListener("click", async () => {
  const res = await fetch("/api/notifications/test", { method: "POST" });
  const data = await res.json();
  showToast("🔔 " + data.message + " Check Windows notifications!");
});

// ─── Add / Edit Task Modal ────────────────────────────────────────────────────
const taskModal = document.getElementById("taskModal");
document.getElementById("openAddModalBtn").addEventListener("click", () => {
  document.getElementById("modalTitle").textContent = "Add New Task";
  document.getElementById("editTaskId").value = "";
  document.getElementById("modalTaskTitle").value = "";
  document.getElementById("modalTaskDate").value = currentDate;
  document.getElementById("modalTaskTime").value = "";
  document.getElementById("modalTaskDuration").value = "30";
  document.getElementById("modalTaskPriority").value = "P2";
  document.getElementById("modalTaskCategory").value = "Work";
  document.getElementById("modalTaskEnergy").value = "Medium";
  taskModal.style.display = "flex";
});
document.getElementById("closeModalBtn").addEventListener("click", () => taskModal.style.display = "none");

function openEditModal(taskId) {
  const task = currentTasks.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById("modalTitle").textContent = "Edit Task";
  document.getElementById("editTaskId").value = task.id;
  document.getElementById("modalTaskTitle").value = task.title;
  document.getElementById("modalTaskDate").value = task.task_date;
  document.getElementById("modalTaskTime").value = task.start_time || "";
  document.getElementById("modalTaskDuration").value = task.duration_minutes || 30;
  document.getElementById("modalTaskPriority").value = task.priority || "P2";
  document.getElementById("modalTaskCategory").value = task.category || "Work";
  document.getElementById("modalTaskEnergy").value = task.energy_level || "Medium";
  taskModal.style.display = "flex";
}

document.getElementById("taskForm").addEventListener("submit", async e => {
  e.preventDefault();
  const editId = document.getElementById("editTaskId").value;
  const payload = {
    title: document.getElementById("modalTaskTitle").value.trim(),
    task_date: document.getElementById("modalTaskDate").value,
    start_time: document.getElementById("modalTaskTime").value || null,
    duration_minutes: parseInt(document.getElementById("modalTaskDuration").value, 10),
    priority: document.getElementById("modalTaskPriority").value,
    category: document.getElementById("modalTaskCategory").value,
    energy_level: document.getElementById("modalTaskEnergy").value,
    is_mit: document.getElementById("modalTaskPriority").value === "P1"
  };
  try {
    if (editId) {
      await fetch(`/api/tasks/${editId}`, { method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    } else {
      await fetch("/api/tasks", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    }
    taskModal.style.display = "none";
    loadTasks();
  } catch (err) { showToast("Error saving task: " + err.message, "error"); }
});

// ─── Pomodoro Timer ───────────────────────────────────────────────────────────
const pomodoroModal = document.getElementById("pomodoroModal");
const pomodoroDisplay = document.getElementById("pomodoroDisplay");
const pomodoroLabel = document.getElementById("pomodoroLabel");
const startBtn = document.getElementById("startPomodoroBtn");
const pauseBtn = document.getElementById("pausePomodoroBtn");
const resetBtn = document.getElementById("resetPomodoroBtn");
let pomodoroTotalSecs = 25 * 60;

document.getElementById("pomodoroBtn").addEventListener("click", () => {
  pomodoroModal.style.display = "flex";
});
document.getElementById("closePomodoroBtn").addEventListener("click", () => {
  pomodoroModal.style.display = "none";
  stopAmbient();
});

document.querySelectorAll(".pomo-mode").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".pomo-mode").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    pomodoroTotalSecs = parseInt(btn.dataset.mins) * 60;
    pomodoroSecondsLeft = pomodoroTotalSecs;
    pomodoroLabel.textContent = btn.dataset.label;
    updatePomodoroDisplay();
    if (pomodoroInterval) { clearInterval(pomodoroInterval); pomodoroInterval = null; }
    pomodoroRunning = false;
    startBtn.disabled = false; pauseBtn.disabled = true;
  });
});

function updatePomodoroDisplay() {
  const m = Math.floor(pomodoroSecondsLeft / 60);
  const s = pomodoroSecondsLeft % 60;
  pomodoroDisplay.textContent = `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
}

startBtn.addEventListener("click", () => {
  if (pomodoroRunning) return;
  pomodoroRunning = true; startBtn.disabled = true; pauseBtn.disabled = false;
  startAmbient(document.getElementById("ambientSelect").value);
  pomodoroInterval = setInterval(() => {
    pomodoroSecondsLeft--;
    updatePomodoroDisplay();
    if (pomodoroSecondsLeft <= 0) {
      clearInterval(pomodoroInterval); pomodoroInterval = null; pomodoroRunning = false;
      stopAmbient();
      startBtn.disabled = false; pauseBtn.disabled = true;
      playDoneChime();
      showToast("🍅 Pomodoro complete! Time for a break.");
    }
  }, 1000);
});

pauseBtn.addEventListener("click", () => {
  if (!pomodoroRunning) return;
  clearInterval(pomodoroInterval); pomodoroInterval = null; pomodoroRunning = false;
  stopAmbient(); startBtn.disabled = false; pauseBtn.disabled = true;
});

resetBtn.addEventListener("click", () => {
  clearInterval(pomodoroInterval); pomodoroInterval = null; pomodoroRunning = false;
  stopAmbient(); pomodoroSecondsLeft = pomodoroTotalSecs;
  updatePomodoroDisplay(); startBtn.disabled = false; pauseBtn.disabled = true;
});

// Ambient sounds using Web Audio API
function getAudioCtx() {
  if (!pomodoroAudioCtx) pomodoroAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return pomodoroAudioCtx;
}

function startAmbient(type) {
  stopAmbient();
  if (type === "none") return;
  try {
    const ctx = getAudioCtx();
    const bufSize = ctx.sampleRate * 2;
    const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buf.getChannelData(0);
    // White noise base
    for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1) * 0.15;

    const src = ctx.createBufferSource();
    src.buffer = buf; src.loop = true;

    const filter = ctx.createBiquadFilter();
    if (type === "brown") { filter.type = "lowpass"; filter.frequency.value = 200; }
    else if (type === "cafe") { filter.type = "bandpass"; filter.frequency.value = 800; filter.Q.value = 0.5; }
    else { filter.type = "highpass"; filter.frequency.value = 100; }

    const gain = ctx.createGain();
    gain.gain.value = type === "rain" ? 0.4 : 0.2;

    src.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
    src.start();
    pomodoroAudioNode = { src, gain };
  } catch (e) { /* audio not available */ }
}

function stopAmbient() {
  if (pomodoroAudioNode) {
    try { pomodoroAudioNode.src.stop(); } catch (e) {}
    pomodoroAudioNode = null;
  }
}

function playDoneChime() {
  try {
    const ctx = getAudioCtx();
    const notes = [523, 659, 784, 1047];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq; osc.type = "sine";
      gain.gain.setValueAtTime(0.3, ctx.currentTime + i * 0.2);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.2 + 0.5);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(ctx.currentTime + i * 0.2);
      osc.stop(ctx.currentTime + i * 0.2 + 0.5);
    });
  } catch (e) {}
}

// ─── Toast Notifications ──────────────────────────────────────────────────────
function showToast(msg, type = "success") {
  const toast = document.createElement("div");
  toast.className = "toast-msg";
  toast.textContent = msg;
  toast.style.cssText = `
    position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
    background: ${type === "error" ? "#ef4444" : "#10b981"};
    color: #fff; padding: 0.75rem 1.2rem; border-radius: 10px;
    font-size: 0.9rem; font-weight: 600; box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    animation: slideInToast 0.3s ease;`;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity 0.4s"; }, 2500);
  setTimeout(() => toast.remove(), 3000);
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ─── Initial Load ─────────────────────────────────────────────────────────────
loadTasks();

// Register PWA Service Worker
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
