// State
let currentDate = new Date().toISOString().split("T")[0];
let currentTasks = [];

// DOM Elements
const liveClock = document.getElementById("liveClock");
const selectedDateInput = document.getElementById("selectedDateInput");
const taskListContainer = document.getElementById("taskListContainer");
const aiAdviceBox = document.getElementById("aiAdviceBox");
const aiAdviceContent = document.getElementById("aiAdviceContent");

// Stat Elements
const statTotal = document.getElementById("statTotal");
const statCompleted = document.getElementById("statCompleted");
const statPercent = document.getElementById("statPercent");
const statMits = document.getElementById("statMits");
const statHours = document.getElementById("statHours");
const statProgressBar = document.getElementById("statProgressBar");

// Initialize Clock
function updateClock() {
  const now = new Date();
  liveClock.textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// Tab Switcher
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
    
    btn.classList.add("active");
    const tabId = btn.dataset.tab;
    const content = document.getElementById(tabId);
    if (content) {
      content.style.display = "block";
    }

    if (tabId === "briefingTab") {
      loadBriefings();
    } else if (tabId === "settingsTab") {
      loadSettings();
    }
  });
});

// Date Navigation
selectedDateInput.value = currentDate;
document.getElementById("nightTargetDate").value = getTomorrowDate();

function getTomorrowDate() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}

selectedDateInput.addEventListener("change", (e) => {
  currentDate = e.target.value;
  loadTasks();
});

document.getElementById("prevDayBtn").addEventListener("click", () => {
  const d = new Date(currentDate);
  d.setDate(d.getDate() - 1);
  currentDate = d.toISOString().split("T")[0];
  selectedDateInput.value = currentDate;
  loadTasks();
});

document.getElementById("nextDayBtn").addEventListener("click", () => {
  const d = new Date(currentDate);
  d.setDate(d.getDate() + 1);
  currentDate = d.toISOString().split("T")[0];
  selectedDateInput.value = currentDate;
  loadTasks();
});

document.getElementById("todayBtn").addEventListener("click", () => {
  currentDate = new Date().toISOString().split("T")[0];
  selectedDateInput.value = currentDate;
  loadTasks();
});

// Load Tasks for Current Date
async function loadTasks() {
  try {
    taskListContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading tasks...</div>`;
    const res = await fetch(`/api/tasks?date=${currentDate}`);
    const data = await res.json();
    currentTasks = data.tasks || [];
    renderTasks();
    updateStats();
  } catch (err) {
    taskListContainer.innerHTML = `<div style="color: var(--accent-rose); padding: 1rem;">Failed to load tasks: ${err.message}</div>`;
  }
}

// Render Task List with Right Checkmark and Cross Buttons
function renderTasks() {
  if (currentTasks.length === 0) {
    taskListContainer.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🌙</div>
        <p style="font-weight: 600; color: var(--text-secondary);">No tasks scheduled for this date.</p>
        <p style="font-size: 0.85rem; margin-top: 0.25rem;">Use the <strong>Bedtime Task Ingestor</strong> tab or click <strong>+ Add Task</strong>.</p>
      </div>
    `;
    return;
  }

  taskListContainer.innerHTML = currentTasks.map(t => {
    const isCompleted = t.status === "completed";
    const isSkipped = t.status === "skipped";
    const priorityClass = `badge-${t.priority.toLowerCase()}`;
    const timeDisplay = t.start_time ? `🕒 ${t.start_time}` : "⏳ Flexible";
    const mitBadge = t.is_mit ? `<span class="badge badge-mit">⭐ MIT</span>` : "";
    
    let statusBadge = "";
    if (isCompleted) {
      statusBadge = `<span class="badge badge-status-done">✔ Completed</span>`;
    } else if (isSkipped) {
      statusBadge = `<span class="badge badge-status-skip">✖ Incomplete / Skipped</span>`;
    }

    return `
      <div class="task-item ${isCompleted ? 'completed' : ''} ${isSkipped ? 'skipped' : ''}" data-id="${t.id}">
        <div class="task-left">
          <!-- Right Checkmark & Cross Buttons -->
          <div class="status-buttons">
            <button 
              type="button" 
              class="btn-status btn-status-check ${isCompleted ? 'active' : ''}" 
              onclick="setTaskStatus(${t.id}, 'completed')" 
              title="Mark as Completed (Right Checkmark)">
              ✔
            </button>
            <button 
              type="button" 
              class="btn-status btn-status-cross ${isSkipped ? 'active' : ''}" 
              onclick="setTaskStatus(${t.id}, 'skipped')" 
              title="Mark as Incomplete / Skipped (Cross)">
              ✖
            </button>
          </div>

          <div class="task-content">
            <div class="task-text">${escapeHtml(t.title)}</div>
            <div class="task-meta">
              <span>${timeDisplay}</span>
              <span>•</span>
              <span>${t.duration_minutes || 30}m</span>
              <span>•</span>
              <span class="badge ${priorityClass}">${t.priority}</span>
              <span class="badge badge-cat">${t.category || 'Work'}</span>
              ${mitBadge}
              ${statusBadge}
            </div>
          </div>
        </div>

        <div class="task-actions">
          <button class="icon-btn" onclick="openEditModal(${t.id})" title="Edit Task">✏️</button>
          <button class="icon-btn icon-btn-delete" onclick="deleteTaskItem(${t.id})" title="Delete Task">🗑️</button>
        </div>
      </div>
    `;
  }).join("");
}

// Update Stats Cards
function updateStats() {
  const total = currentTasks.length;
  const completed = currentTasks.filter(t => t.status === "completed").length;
  const mits = currentTasks.filter(t => t.is_mit && t.status !== "completed").length;
  const totalMins = currentTasks.reduce((acc, t) => acc + (t.duration_minutes || 30), 0);
  const totalHours = (totalMins / 60).toFixed(1);
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  statTotal.textContent = total;
  statCompleted.textContent = completed;
  statPercent.textContent = `${percent}% finished`;
  statMits.textContent = mits;
  statHours.textContent = `${totalHours}h`;
  statProgressBar.style.width = `${percent}%`;
}

// Toggle or Set Task Status (completed, skipped, or pending)
async function setTaskStatus(taskId, targetStatus) {
  const task = currentTasks.find(t => t.id === taskId);
  if (!task) return;

  // Toggle back to pending if clicked again
  const newStatus = task.status === targetStatus ? "pending" : targetStatus;

  try {
    await fetch(`/api/tasks/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    task.status = newStatus;
    renderTasks();
    updateStats();
  } catch (err) {
    alert("Error updating task: " + err.message);
  }
}

// Delete Task
async function deleteTaskItem(taskId) {
  if (!confirm("Delete this task?")) return;
  try {
    await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
    currentTasks = currentTasks.filter(t => t.id !== taskId);
    renderTasks();
    updateStats();
  } catch (err) {
    alert("Error deleting task: " + err.message);
  }
}

// AI Optimize Routine
document.getElementById("optimizeScheduleBtn").addEventListener("click", async () => {
  const btn = document.getElementById("optimizeScheduleBtn");
  btn.disabled = true;
  btn.textContent = "✨ Optimizing...";

  try {
    const res = await fetch("/api/agent/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: currentDate })
    });
    const data = await res.json();
    if (data.status === "success") {
      aiAdviceBox.style.display = "block";
      aiAdviceContent.textContent = data.agent_advice || data.message;
      loadTasks();
    } else {
      alert(data.message || "Optimization finished.");
    }
  } catch (err) {
    alert("Optimization error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ AI Optimize Routine";
  }
});

// Night Ingestor Submission
document.getElementById("submitNightTasksBtn").addEventListener("click", async () => {
  const rawText = document.getElementById("nightTextInput").value.trim();
  const targetDate = document.getElementById("nightTargetDate").value;

  if (!rawText) {
    alert("Please enter some tasks before submitting.");
    return;
  }

  const btn = document.getElementById("submitNightTasksBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Parsing & Scheduling...";

  try {
    const res = await fetch("/api/tasks/bulk-night-entry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, target_date: targetDate })
    });
    const data = await res.json();

    if (data.status === "success") {
      alert(`🎉 Successfully parsed and scheduled ${data.tasks_created} tasks for ${data.target_date}!`);
      document.getElementById("nightTextInput").value = "";
      
      // Auto optimize
      await fetch("/api/agent/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: targetDate })
      });

      // Switch to schedule tab
      currentDate = targetDate;
      selectedDateInput.value = currentDate;
      document.querySelector('[data-tab="scheduleTab"]').click();
      loadTasks();
    }
  } catch (err) {
    alert("Error scheduling tasks: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "🚀 Parse, Schedule & Notify Tomorrow";
  }
});

// Templates for Bedtime Ingestor
function applyTemplate(type) {
  const textarea = document.getElementById("nightTextInput");
  if (type === "productive") {
    textarea.value = `- Wake up at 7:00 AM #routine
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
    textarea.value = `- Wake up at 6:30 AM & Hydrate
- 5km Morning Run & Workout at 7:00 AM for 1 hour [High] [P1]
- High Protein Breakfast at 8:30 AM
- Deep Focus Work Block at 10:00 AM for 3 hours [P1]
- Afternoon Mobility & Stretch at 3:00 PM for 20 mins
- Evening Walk in nature at 6:00 PM
- Healthy Meal Prep at 7:30 PM
- Foam Roll & Sleep at 10:00 PM`;
  } else if (type === "study") {
    textarea.value = `- Wake up at 7:30 AM #routine
- Algorithm & Coding Practice at 8:30 AM for 90 mins [P1] [High]
- Research Paper Reading at 11:00 AM for 1 hour [P2]
- Break & Lunch at 12:30 PM
- System Design Course Module at 2:00 PM for 2 hours [P1]
- Flashcards & Note Review at 5:00 PM for 45 mins
- Evening Relaxation & Walk at 7:00 PM
- Sleep at 11:00 PM`;
  }
}

// Briefing & Reflection Loader
async function loadBriefings() {
  try {
    const morningRes = await fetch(`/api/agent/briefing?date=${currentDate}`);
    const morningData = await morningRes.json();
    document.getElementById("morningDigestBox").innerHTML = `
      <h4 style="color: #fbbf24; margin-bottom: 0.5rem;">${morningData.title}</h4>
      <p style="color: #f1f5f9; font-size: 0.95rem;">${morningData.message}</p>
      <div style="margin-top: 0.8rem; font-size: 0.85rem; color: var(--text-secondary);">
        <strong>Planned Tasks:</strong> ${morningData.task_count || 0}
      </div>
    `;

    const eveningRes = await fetch(`/api/agent/reflection?date=${currentDate}`);
    const eveningData = await eveningRes.json();
    document.getElementById("eveningDigestBox").innerHTML = `
      <h4 style="color: #c084fc; margin-bottom: 0.5rem;">${eveningData.title}</h4>
      <p style="color: #f1f5f9; font-size: 0.95rem;">${eveningData.message}</p>
      ${eveningData.pending_tasks && eveningData.pending_tasks.length > 0 ? `
        <div style="margin-top: 0.8rem; font-size: 0.85rem; color: #fb7185;">
          <strong>Unfinished to rollover:</strong> ${eveningData.pending_tasks.join(", ")}
        </div>
      ` : `<div style="margin-top: 0.8rem; font-size: 0.85rem; color: #10b981;">🎉 All scheduled tasks wrapped up!</div>`}
    `;
  } catch (err) {
    console.error("Failed to load briefings:", err);
  }
}

// Settings
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    document.getElementById("set_email_recipient").value = data.email_recipient || "";
    document.getElementById("set_email_sender").value = data.email_sender || "";
    document.getElementById("set_email_smtp_password").value = data.email_smtp_password || "";
    document.getElementById("set_enable_email_notifications").value = data.enable_email_notifications || "true";
    document.getElementById("set_email_smtp_host").value = data.email_smtp_host || "smtp.gmail.com";
    document.getElementById("set_email_smtp_port").value = data.email_smtp_port || "587";

    document.getElementById("set_morning_briefing_time").value = data.morning_briefing_time || "07:30";
    document.getElementById("set_evening_planning_time").value = data.evening_planning_time || "22:00";
    document.getElementById("set_notify_lead_minutes").value = data.notify_lead_minutes || "10";
    document.getElementById("set_enable_audio_chime").value = data.enable_audio_chime || "true";
    document.getElementById("set_discord_webhook_url").value = data.discord_webhook_url || "";
    document.getElementById("set_telegram_bot_token").value = data.telegram_bot_token || "";
    document.getElementById("set_telegram_chat_id").value = data.telegram_chat_id || "";
  } catch (err) {
    console.error("Settings load error:", err);
  }
}

document.getElementById("settingsForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    email_recipient: document.getElementById("set_email_recipient").value,
    email_sender: document.getElementById("set_email_sender").value,
    email_smtp_password: document.getElementById("set_email_smtp_password").value,
    enable_email_notifications: document.getElementById("set_enable_email_notifications").value,
    email_smtp_host: document.getElementById("set_email_smtp_host").value,
    email_smtp_port: document.getElementById("set_email_smtp_port").value,
    morning_briefing_time: document.getElementById("set_morning_briefing_time").value,
    evening_planning_time: document.getElementById("set_evening_planning_time").value,
    notify_lead_minutes: document.getElementById("set_notify_lead_minutes").value,
    enable_audio_chime: document.getElementById("set_enable_audio_chime").value,
    discord_webhook_url: document.getElementById("set_discord_webhook_url").value,
    telegram_bot_token: document.getElementById("set_telegram_bot_token").value,
    telegram_chat_id: document.getElementById("set_telegram_chat_id").value
  };

  try {
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert("✅ Settings saved successfully!");
  } catch (err) {
    alert("Error saving settings: " + err.message);
  }
});

// Test Email Buttons
async function triggerTestEmail() {
  const recipient = document.getElementById("set_email_recipient").value;
  if (!recipient) {
    alert("Please enter a recipient email address in the Email Settings first.");
    return;
  }
  
  const payload = {
    email_recipient: document.getElementById("set_email_recipient").value,
    email_sender: document.getElementById("set_email_sender").value,
    email_smtp_password: document.getElementById("set_email_smtp_password").value,
    enable_email_notifications: document.getElementById("set_enable_email_notifications").value,
    email_smtp_host: document.getElementById("set_email_smtp_host").value,
    email_smtp_port: document.getElementById("set_email_smtp_port").value
  };
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  try {
    const res = await fetch("/api/notifications/test-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient })
    });
    const data = await res.json();
    if (res.ok) {
      alert("📧 " + data.message);
    } else {
      alert("❌ Email Error: " + data.detail);
    }
  } catch (err) {
    alert("Error triggering email: " + err.message);
  }
}

document.getElementById("testEmailBtn").addEventListener("click", triggerTestEmail);
document.getElementById("quickTestEmailBtn").addEventListener("click", () => {
  document.querySelector('[data-tab="settingsTab"]').click();
  triggerTestEmail();
});

// Test Windows Notification Button
document.getElementById("testNotifyBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/api/notifications/test", { method: "POST" });
    const data = await res.json();
    alert("🔔 " + data.message + " Check your Windows notification center!");
  } catch (err) {
    alert("Error triggering notification: " + err.message);
  }
});

// Modal Controls
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

document.getElementById("closeModalBtn").addEventListener("click", () => {
  taskModal.style.display = "none";
});

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

document.getElementById("taskForm").addEventListener("submit", async (e) => {
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
      await fetch(`/api/tasks/${editId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } else {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }
    taskModal.style.display = "none";
    loadTasks();
  } catch (err) {
    alert("Error saving task: " + err.message);
  }
});

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Initial Load
loadTasks();
