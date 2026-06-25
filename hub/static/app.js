const state = { t: {}, user: null, csrf: null, view: "dashboard", locale: "en", locales: ["en"] };
const localeNames = { en: "English", de: "Deutsch", es: "Español", fr: "Français" };
const $ = selector => document.querySelector(selector);
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
const tr = key => state.t[key] || key;
const preferredLocale = () => localStorage.getItem("hub.locale") || navigator.language || "en";

async function api(path, opts = {}) {
  opts.headers = { ...(opts.headers || {}) };
  if (state.csrf) opts.headers["X-CSRF-Token"] = state.csrf;
  if (opts.body && typeof opts.body !== "string") {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const response = await fetch(path, opts);
  if (response.status === 401) {
    showLogin();
    throw new Error(tr("error.auth_required"));
  }
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

function clear() {
  const view = $("#view");
  view.replaceChildren();
  return view;
}

function applyStaticText() {
  document.documentElement.lang = state.locale;
  document.title = tr("app.title");
  $("#brand").textContent = tr("app.title");
  $("#loginTitle").textContent = tr("app.title");
  $("#logout").textContent = tr("common.logout");
  $("#username").placeholder = tr("auth.username");
  $("#password").placeholder = tr("auth.password");
  $("#loginSubmit").textContent = tr("auth.submit");
  $("#title").textContent = tr("app.title");
  $("#subtitle").textContent = tr("app.subtitle");
  renderLocalePicker();
}

function renderLocalePicker() {
  const select = $("#locale");
  select.replaceChildren();
  state.locales.forEach(locale => {
    const option = el("option", localeNames[locale] || locale);
    option.value = locale;
    option.selected = locale === state.locale;
    select.append(option);
  });
  select.title = tr("common.language");
  select.hidden = state.locales.length < 2;
}

function showLogin() {
  $("#login").hidden = false;
  $("#workspace").hidden = true;
  $("#logout").hidden = true;
}

function showWorkspace() {
  $("#login").hidden = true;
  $("#workspace").hidden = false;
  $("#logout").hidden = false;
  renderNav();
  render();
}

function renderNav() {
  const nav = $("#nav");
  nav.replaceChildren();
  ["dashboard", "chat", "compare", "research", "creative", "notes", "calendar", "services", "queue", "setup"].forEach(id => {
    const link = el("a", tr("nav." + id));
    link.href = "#" + id;
    link.className = id === state.view ? "active" : "";
    link.onclick = event => {
      event.preventDefault();
      state.view = id;
      location.hash = id;
      renderNav();
      render();
    };
    nav.append(link);
  });
}

function card(title, value) {
  const container = el("div", undefined, "card");
  container.append(el("h3", title), typeof value === "string" ? el("p", value) : value);
  return container;
}

function formPanel(title) {
  const panel = el("section", undefined, "panel stack");
  panel.append(el("h2", title));
  return panel;
}

async function dashboard() {
  const data = await api("/api/dashboard");
  const view = clear();
  const grid = el("div", undefined, "grid");
  const hardware = data.hardware;
  const accelerators = hardware.accelerators.map(item => `${item.name} · ${Math.round(item.memory_mib / 1024)} GiB`).join("\n") || tr("hardware.cpu_only");
  grid.append(
    card(tr("dashboard.hardware"), `${hardware.system} ${hardware.machine}\n${accelerators}`),
    card(tr("dashboard.topology"), `${hardware.recommendation.topology} — ${hardware.recommendation.reason}`),
    card(tr("dashboard.services"), String(data.services.length)),
    card(tr("dashboard.jobs"), String(data.jobs.length))
  );
  view.append(grid);
}

async function chat() {
  const view = clear();
  const panel = formPanel(tr("nav.chat"));
  const model = el("input");
  model.placeholder = tr("common.model");
  model.value = "qwen3.5:9b";
  const prompt = el("textarea");
  prompt.placeholder = tr("common.prompt");
  const output = el("pre", "");
  const button = el("button", tr("common.send"));
  button.onclick = async () => {
    button.disabled = true;
    try {
      const response = await api("/api/chat", { method: "POST", body: { prompt: prompt.value, model: model.value } });
      output.textContent = response.response || response.thinking;
    } catch (error) {
      output.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
  panel.append(model, prompt, button, output);
  view.append(panel);
}

async function compare() {
  const view = clear();
  const panel = formPanel(tr("nav.compare"));
  const models = el("input");
  models.placeholder = tr("compare.models_placeholder");
  models.value = "qwen3.5:9b,qwen2.5-coder:14b";
  const prompt = el("textarea");
  prompt.placeholder = tr("common.prompt");
  const output = el("div", undefined, "grid");
  const button = el("button", tr("common.compare"));
  button.onclick = async () => {
    output.replaceChildren();
    const targets = models.value.split(",").map(model => ({ model: model.trim() })).filter(item => item.model);
    for (const response of await api("/api/compare", { method: "POST", body: { prompt: prompt.value, targets } })) {
      output.append(card(response.model, response.response || response.error || ""));
    }
  };
  panel.append(models, prompt, button, output);
  view.append(panel);
}

async function research() {
  const view = clear();
  const panel = formPanel(tr("nav.research"));
  const query = el("input");
  query.placeholder = tr("research.query_placeholder");
  const output = el("div", undefined, "stack");
  const button = el("button", tr("common.search"));
  button.onclick = async () => {
    output.replaceChildren();
    try {
      const response = await api("/api/research", { method: "POST", body: { query: query.value } });
      response.results.forEach(result => {
        const link = el("a", result.title);
        link.href = result.url;
        link.target = "_blank";
        output.append(card("", link), el("p", result.content || ""));
      });
    } catch (error) {
      output.append(el("p", error.message));
    }
  };
  panel.append(query, button, output);
  view.append(panel);
}

async function creative() {
  const view = clear();
  const panel = formPanel(tr("nav.creative"));
  const open = el("a", tr("creative.open"), "button");
  open.href = `${location.protocol}//${location.hostname}:8188/`;
  open.target = "_blank";
  const grid = el("div", undefined, "grid");
  const data = await api("/api/workflows");
  data.workflows.forEach(workflow => {
    const download = el("a", tr("creative.download"), "button");
    download.href = "/workflows/" + encodeURIComponent(workflow.file);
    const workflowCard = card(workflow.title, workflow.tier);
    workflowCard.append(download);
    grid.append(workflowCard);
  });
  panel.append(open, el("p", tr("creative.models")), grid);
  view.append(panel);
}

async function notes() {
  const view = clear();
  const grid = el("div", undefined, "grid");
  for (const kind of ["notes", "tasks"]) {
    const panel = formPanel(tr(kind === "notes" ? "notes.title" : "tasks.title"));
    const title = el("input");
    title.placeholder = tr("common.title");
    const detail = el("textarea");
    detail.placeholder = tr(kind === "notes" ? "notes.body" : "tasks.detail");
    const list = el("div");
    const button = el("button", tr("common.add"));
    button.onclick = async () => {
      await api("/api/" + kind, { method: "POST", body: kind === "notes" ? { title: title.value, body: detail.value } : { title: title.value, detail: detail.value } });
      render();
    };
    const data = await api("/api/" + kind);
    data.forEach(item => {
      const row = el("div", undefined, "item");
      row.append(el("strong", item.title), el("p", item.body || item.detail || ""));
      const del = el("button", tr("common.delete"), "danger");
      del.onclick = async () => {
        await api("/api/" + kind + "/" + item.id, { method: "DELETE" });
        render();
      };
      row.append(del);
      list.append(row);
    });
    panel.append(title, detail, button, list);
    grid.append(panel);
  }
  view.append(grid);
}

async function calendar() {
  const view = clear();
  const panel = formPanel(tr("nav.calendar"));
  const title = el("input");
  title.placeholder = tr("common.title");
  const start = el("input");
  start.type = "datetime-local";
  start.title = tr("calendar.starts_at");
  const button = el("button", tr("common.add"));
  const list = el("div");
  button.onclick = async () => {
    await api("/api/events", { method: "POST", body: { title: title.value, starts_at: new Date(start.value).getTime() / 1000 } });
    render();
  };
  (await api("/api/events")).forEach(item => list.append(card(item.title, new Date(item.starts_at * 1000).toLocaleString(state.locale))));
  panel.append(title, start, button, list);
  view.append(panel);
}

async function services() {
  const view = clear();
  const panel = formPanel(tr("nav.services"));
  const name = el("input");
  const kind = el("input");
  const url = el("input");
  const button = el("button", tr("common.add"));
  const list = el("div");
  name.placeholder = tr("service.name");
  kind.placeholder = tr("service.kind");
  url.placeholder = tr("service.url");
  button.onclick = async () => {
    await api("/api/services", { method: "POST", body: { name: name.value, kind: kind.value, base_url: url.value } });
    render();
  };
  (await api("/api/services")).forEach(service => {
    const item = el("div", undefined, "item");
    const link = el("a", `${service.name} · ${service.kind} · ${service.last_status || tr("status.unknown")}`);
    link.href = service.base_url;
    link.target = "_blank";
    item.append(link);
    list.append(item);
  });
  panel.append(name, kind, url, button, list);
  view.append(panel);
}

async function queue() {
  const view = clear();
  const panel = formPanel(tr("nav.queue"));
  const model = el("input");
  model.placeholder = tr("common.model");
  model.value = "qwen3.5:9b";
  const prompt = el("textarea");
  prompt.placeholder = tr("common.prompt");
  const mode = el("select");
  ["auto", "sequential", "parallel", "broadcast", "pipeline", "gang"].forEach(value => {
    const option = el("option", tr("queue.mode." + value));
    option.value = value;
    mode.append(option);
  });
  const button = el("button", tr("queue.submit"));
  const list = el("div");
  button.onclick = async () => {
    await api("/api/jobs", { method: "POST", body: { kind: "ollama.generate", mode: mode.value, payload: { model: model.value, prompt: prompt.value } } });
    setTimeout(render, 500);
  };
  (await api("/api/jobs")).forEach(job => list.append(card(`${job.kind} · ${job.status}`, job.result_summary || job.error || job.id)));
  panel.append(model, prompt, mode, button, list);
  view.append(panel);
}

async function setup() {
  const view = clear();
  const panel = formPanel(tr("nav.setup"));
  const network = el("input");
  const output = el("div", undefined, "grid");
  const button = el("button", tr("common.discover"));
  network.placeholder = tr("setup.network_placeholder");
  button.onclick = async () => {
    output.replaceChildren();
    try {
      const found = await api("/api/discovery/scan", { method: "POST", body: { network: network.value } });
      if (!found.length) output.append(el("p", tr("common.no_services")));
      found.forEach(service => {
        const serviceCard = card(service.kind, `${service.base_url} · HTTP ${service.status_code}`);
        const add = el("button", tr("common.add"));
        add.onclick = async () => {
          await api("/api/services", { method: "POST", body: { name: service.name, kind: service.kind, base_url: service.base_url } });
          add.disabled = true;
          add.textContent = tr("common.added");
        };
        serviceCard.append(add);
        output.append(serviceCard);
      });
    } catch (error) {
      output.append(el("p", error.message));
    }
  };
  const models = await api("/api/models");
  panel.append(network, button, output, el("h3", tr("setup.model_profiles")), el("pre", JSON.stringify(models, null, 2)));
  view.append(panel);
}

async function render() {
  const fn = { dashboard, chat, compare, research, creative, notes, calendar, services, queue, setup }[state.view] || dashboard;
  try {
    await fn();
  } catch (error) {
    clear().append(el("p", error.message));
  }
}

async function boot(locale = preferredLocale()) {
  state.view = location.hash.slice(1) || "dashboard";
  const bootstrap = await api("/api/bootstrap?locale=" + encodeURIComponent(locale));
  state.t = bootstrap.translations;
  state.locale = bootstrap.locale;
  state.locales = bootstrap.available_locales || [bootstrap.locale];
  state.user = bootstrap.user;
  localStorage.setItem("hub.locale", state.locale);
  applyStaticText();
  if (bootstrap.user) {
    state.csrf = bootstrap.user.csrf_token;
    showWorkspace();
  } else {
    showLogin();
  }
}

$("#locale").onchange = event => boot(event.target.value);
$("#loginForm").onsubmit = async event => {
  event.preventDefault();
  try {
    const response = await api("/api/auth/login", { method: "POST", body: { username: $("#username").value, password: $("#password").value } });
    state.user = response;
    state.csrf = response.csrf_token;
    boot(state.locale);
  } catch (error) {
    $("#loginError").textContent = error.message;
  }
};
$("#logout").onclick = async () => {
  await api("/api/auth/logout", { method: "POST" });
  state.user = null;
  state.csrf = null;
  showLogin();
};
boot();
