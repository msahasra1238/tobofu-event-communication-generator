
const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "tobofu-events-v1";

let events = [];
try {
  events = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  if (!Array.isArray(events)) events = [];
} catch {
  events = [];
}

let activeEventId = null;
let toastTimer;

const today = new Date();
const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000)
  .toISOString().slice(0, 10);
$("event-date").min = localDate;
$("event-deadline").min = localDate;

function saveEvents() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  } catch {
    showToast("Browser storage is unavailable. Try another browser.");
  }
  renderEvents();
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2400);
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;"
  })[ch]);
}

function getActiveEvent() {
  return events.find(event => event.id === activeEventId) || events[0] || null;
}

function formatDate(date) {
  if (!date) return "Date not set";
  return new Date(date + "T12:00:00").toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric"
  });
}

function renderEvents() {
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date));
  const upcoming = sorted.filter(event => event.date >= localDate);

  $("event-count").textContent = events.length;
  $("upcoming-count").textContent = upcoming.length;

  $("upcoming-list").innerHTML = upcoming.length
    ? upcoming.slice(0, 4).map(event => `
      <div class="upcoming-item">
        <div class="date-block">
          <strong>${escapeHTML(event.date.slice(8, 10))}</strong>
          <small>${escapeHTML(new Date(event.date + "T12:00:00")
            .toLocaleDateString("en-IN", { month: "short" }))}</small>
        </div>
        <div class="event-meta">
          <strong>${escapeHTML(event.name)}</strong>
          <small>${escapeHTML(event.venue || "Venue to be announced")}</small>
        </div>
        <button class="copy-btn select-event" data-id="${escapeHTML(event.id)}">Use</button>
      </div>`).join("")
    : '<p class="empty">No upcoming events yet. Create your first event!</p>';

  $("calendar-list").innerHTML = sorted.length
    ? sorted.flatMap(event => [
      { date: event.date, title: event.name, type: "Event day", id: event.id },
      ...(event.deadline ? [{
        date: event.deadline, title: event.name,
        type: "Registration deadline", id: event.id
      }] : [])
    ]).sort((a, b) => a.date.localeCompare(b.date))
      .map(item => `
        <div class="calendar-item">
          <div class="date-block">
            <strong>${escapeHTML(item.date.slice(8, 10))}</strong>
            <small>${escapeHTML(new Date(item.date + "T12:00:00")
              .toLocaleDateString("en-IN", { month: "short" }))}</small>
          </div>
          <div class="event-meta">
            <strong>${escapeHTML(item.title)}</strong>
            <small>${escapeHTML(item.type)} · ${escapeHTML(formatDate(item.date))}</small>
          </div>
          <button class="delete-btn delete-event" data-id="${escapeHTML(item.id)}"
            aria-label="Delete event">×</button>
        </div>`).join("")
    : '<p class="empty">Save an event to add dates to your schedule.</p>';
}

function openPage(page) {
  const titles = {
    dashboard: "Your event workspace",
    create: "Create an event",
    content: "Message studio",
    faqs: "Frequently asked questions",
    emails: "Email generator",
    calendar: "Reminder calendar"
  };

  $("page-title").textContent = titles[page] || titles.dashboard;
  document.querySelectorAll(".nav").forEach(button => {
    button.classList.toggle("active", button.dataset.page === page);
  });

  if (page === "create") {
    $("event-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    $("event-name").focus({ preventScroll: true });
  } else if (page === "calendar") {
    $("calendar-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (["content", "faqs", "emails"].includes(page)) {
    generateContent(page === "faqs" ? "faq" : page === "emails" ? "email" : "caption");
    $("results-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

document.querySelectorAll(".nav").forEach(button => {
  button.addEventListener("click", () => openPage(button.dataset.page));
});

$("new-event-btn").addEventListener("click", () => openPage("create"));
$("hero-create").addEventListener("click", () => openPage("create"));
$("view-calendar").addEventListener("click", () => openPage("calendar"));

$("event-form").addEventListener("submit", event => {
  event.preventDefault();

  const name = $("event-name").value.trim();
  const description = $("event-description").value.trim();
  const date = $("event-date").value;
  const deadline = $("event-deadline").value;

  if (!name || !description || !date) {
    showToast("Please fill in the required fields.");
    return;
  }
  if (deadline && deadline > date) {
    showToast("Registration deadline should be on or before the event date.");
    return;
  }

  const data = {
    name, description, date, deadline,
    time: $("event-time").value,
    venue: $("event-venue").value.trim(),
    audience: $("event-audience").value.trim(),
    link: $("event-link").value.trim()
  };

  const existing = events.find(item => item.id === activeEventId);
  if (existing) {
    Object.assign(existing, data);
  } else {
    activeEventId = String(Date.now()) + Math.random().toString(36).slice(2, 7);
    events.push({ id: activeEventId, ...data });
  }

  saveEvents();
  showToast("Event saved successfully!");
  generateContent("caption");
});

$("upcoming-list").addEventListener("click", event => {
  const button = event.target.closest(".select-event");
  if (!button) return;
  activeEventId = button.dataset.id;
  const item = getActiveEvent();
  if (!item) return;

  $("event-name").value = item.name;
  $("event-description").value = item.description;
  $("event-date").value = item.date;
  $("event-time").value = item.time || "";
  $("event-venue").value = item.venue || "";
  $("event-audience").value = item.audience || "";
  $("event-deadline").value = item.deadline || "";
  $("event-link").value = item.link || "";
  showToast("Event selected. You can edit it.");
  openPage("create");
});

$("calendar-list").addEventListener("click", event => {
  const button = event.target.closest(".delete-event");
  if (!button) return;
  const item = events.find(event => event.id === button.dataset.id);
  if (!item) return;
  if (!confirm(`Delete "${item.name}" and its saved dates?`)) return;

  events = events.filter(event => event.id !== item.id);
  if (activeEventId === item.id) activeEventId = null;
  saveEvents();
  showToast("Event deleted.");
});

function buildContent(type, event) {
  const name = event.name;
  const date = formatDate(event.date);
  const venue = event.venue || "Venue to be announced";
  const audience = event.audience || "everyone interested";
  const link = event.link || "Registration details to be announced";
  const deadline = event.deadline ? formatDate(event.deadline) : "To be announced";
  const time = event.time || "To be announced";

  switch (type) {
    case "caption":
      return [{
        title: "Social media caption",
        body: `✨ Save the date! ${name}\n\n${event.description}\n\n📅 ${date} · ${time}\n📍 ${venue}\n\nCalling all ${audience}! Be part of the experience.\nRegister: ${link}\n\n#${name.replace(/[^a-zA-Z0-9]/g, "")} #CampusEvents`
      }, {
        title: "Short promotional caption",
        body: `${name} is coming! 🎉\n${event.description}\nJoin us on ${date}.\nRegistration: ${link}`
      }];

    case "whatsapp":
      return [{
        title: "WhatsApp invitation",
        body: `👋 Hello!\n\nYou're invited to *${name}*!\n\n${event.description}\n\n📅 Date: ${date}\n⏰ Time: ${time}\n📍 Venue: ${venue}\n\n🔗 Registration: ${link}\n\nWe hope to see you there!`
      }, {
        title: "Registration reminder",
        body: `⏰ Reminder: ${name}\n\nDon't forget to register for our upcoming event on ${date}.\nRegistration deadline: ${deadline}\n\nRegister here: ${link}\n\nPlease check the event details before attending.`
      }];

    case "announcement":
      return [{
        title: "Official event announcement",
        body: `ANNOUNCEMENT: ${name}\n\nWe are pleased to announce ${name}, an event for ${audience}.\n\nAbout the event: ${event.description}\n\nDate: ${date}\nTime: ${time}\nVenue: ${venue}\nRegistration deadline: ${deadline}\n\nRegistration details: ${link}\n\nPlease follow the organizer's official updates for any changes.`
      }];

    case "faq":
      return [{
        title: "Frequently asked questions",
        body: `Q: What is ${name}?\nA: ${event.description}\n\nQ: When is the event?\nA: ${date}, at ${time}.\n\nQ: Where will it take place?\nA: ${venue}.\n\nQ: Who can attend?\nA: The intended audience is ${audience}. Confirm eligibility with the organizer.\n\nQ: How can I register?\nA: ${link}\n\nQ: What is the registration deadline?\nA: ${deadline}.\n\nQ: Will participants receive certificates?\nA: Please confirm certificate availability with the organizer.`
      }];

    case "email":
      return [{
        title: "Email invitation",
        body: `Subject: You're invited to ${name}!\n\nDear ${audience},\n\nWe are delighted to invite you to ${name}.\n\n${event.description}\n\nEvent details:\nDate: ${date}\nTime: ${time}\nVenue: ${venue}\nRegistration deadline: ${deadline}\n\nPlease register here: ${link}\n\nWe look forward to your participation.\n\nBest regards,\nThe ${name} Organizing Team`
      }];

    case "reminder":
      return [{
        title: "Reminder schedule",
        body: `EVENT: ${name}\n\n${event.deadline ? `• Registration deadline: ${deadline}\n• Suggested reminder: 1 day before registration closes\n` : "• Add a registration deadline to plan deadline reminders.\n"}• Event date: ${date}\n• Suggested event reminder: 1 day before the event\n• Event time: ${time}\n• Venue: ${venue}\n\nThese are suggested reminders only. This demo does not send automatic notifications.`
      }];
    default:
      return [];
  }
}

const typeTitles = {
  caption: "Social media captions",
  whatsapp: "WhatsApp messages",
  announcement: "Announcements",
  faq: "Frequently asked questions",
  email: "Email generator",
  reminder: "Reminder planner"
};


async function generateContent(type) {
  const event = getActiveEvent();

  $("result-title").textContent = typeTitles[type] || "Message studio";

  if (!event) {
    $("result-description").textContent =
      "Create an event first to generate content.";
    $("results").innerHTML =
      '<div class="empty large">Please save an event first.</div>';
    return;
  }

  $("result-description").textContent = "Generating content with Gemini AI...";
  $("results").innerHTML =
    '<div class="empty large">✦ TOBOFU AI is creating your content...</div>';

  try {
    const response = await fetch("http://127.0.0.1:5000/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: event.name,
        description: event.description,
        date: event.date,
        time: event.time,
        venue: event.venue,
        audience: event.audience,
        deadline: event.deadline,
        link: event.link,
        type: type
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "AI generation failed.");
    }

    const content = data.content || "No content returned.";
    $("result-description").textContent =
      `AI-generated content for "${event.name}".`;

    $("results").innerHTML = `
      <article class="result-card">
        <div class="result-top">
          <strong>${escapeHTML(typeTitles[type] || "Generated content")}</strong>
          <button class="copy-btn" id="copy-ai-content">Copy text</button>
        </div>
        <div class="result-body">${escapeHTML(content)}</div>
      </article>`;

    $("results").dataset.content = JSON.stringify([
      { title: typeTitles[type] || "Generated content", body: content }
    ]);

    $("copy-ai-content").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(content);
        showToast("AI content copied!");
      } catch {
        showToast("Copy unavailable. Please select the text manually.");
      }
    });
  } catch (error) {
    $("result-description").textContent = "Could not generate content.";
    $("results").innerHTML =
      `<div class="empty large">${escapeHTML(error.message)}<br>
      Check that the Python backend is running.</div>`;
  }
}

document.querySelectorAll(".tool").forEach(button => {
  button.addEventListener("click", () => {
    generateContent(button.dataset.type);
    $("results-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

$("results").addEventListener("click", async event => {
  const button = event.target.closest("[data-copy-index]");
  if (!button) return;

  const items = JSON.parse($("results").dataset.content || "[]");
  const item = items[Number(button.dataset.copyIndex)];
  if (!item) return;

  try {
    await navigator.clipboard.writeText(item.body);
    showToast("Content copied!");
  } catch {
    const area = document.createElement("textarea");
    area.value = item.body;
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    showToast(copied ? "Content copied!" : "Copy failed. Select the text manually.");
  }
});

renderEvents();
