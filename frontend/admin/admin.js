// 管理端逻辑（体验版：仅修改示例智能体；知识库为单一文本框）
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

let currentSlug = null;
let currentSettings = null;
let editingModelId = null;

// 视图切换
function showView(name) {
  $$(".view").forEach((v) => v.classList.add("hidden"));
  $("#view-" + name).classList.remove("hidden");
}

function setActiveNav(view) {
  $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
}

// 渲染列表
async function loadList() {
  setActiveNav("list");
  const res = await fetch("/api/agents");
  const agents = await res.json();
  const grid = $("#agent-grid");
  grid.innerHTML = "";
  if (agents.length === 0) {
    grid.innerHTML = '<p class="hint">还没有智能体。</p>';
    return;
  }
  agents.forEach((a) => {
    const ava = a.avatar
      ? `<img src="/data/agents/${a.slug}/${a.avatar}" />`
      : "🙂";
    const badge = a.published
      ? '<span class="badge">已发布</span>'
      : '<span class="badge off">未发布</span>';
    const card = document.createElement("div");
    card.className = "agent-card";
    const copyBtn = a.published ? '<button data-act="copy">复制链接</button>' : "";
    card.innerHTML = `
      <div class="top">
        <div class="ava">${ava}</div>
        <div><div class="name">${esc(a.name)}${badge}</div></div>
      </div>
      <div class="card-actions">
        <button data-act="debug">调试</button>
        <button data-act="edit">修改</button>
        ${copyBtn}
        <button data-act="del" class="del">删除</button>
      </div>`;
    card.querySelector('[data-act="debug"]').onclick = () => openDebug(a.slug);
    card.querySelector('[data-act="edit"]').onclick = () => openEdit(a.slug);
    card.querySelector('[data-act="del"]').onclick = () => delAgent(a.slug);
    const cp = card.querySelector('[data-act="copy"]');
    if (cp) cp.onclick = () => copyText(`${location.origin}/c/${a.slug}`, cp);
    grid.appendChild(card);
  });
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ========== 模型设置 ==========
async function loadSettings() {
  setActiveNav("settings");
  const res = await fetch("/api/settings");
  currentSettings = await res.json();
  renderModelsGrid();
  showView("settings");
}

function renderModelsGrid() {
  const grid = $("#models-grid");
  grid.innerHTML = "";
  const models = (currentSettings && currentSettings.models) || [];
  const defaultId = currentSettings && currentSettings.default_model;
  if (models.length === 0) {
    grid.innerHTML = '<p class="hint">还没有添加模型。</p>';
    return;
  }
  models.forEach((m) => {
    const isDefault = m.id === defaultId;
    const card = document.createElement("div");
    card.className = "model-card";
    card.innerHTML = `
      <div class="model-icon">☁️</div>
      <div class="model-info">
        <div class="model-name">${esc(m.name || m.model_id)}
          ${isDefault ? '<span class="badge">默认</span>' : ''}
        </div>
        <div class="model-meta">${esc(m.model_id || "")}</div>
      </div>
      <div class="model-actions">
        ${isDefault ? '' : '<button class="btn-ghost set-default" title="设为默认">设为默认</button>'}
        <button class="btn-ghost edit" title="编辑">✏️</button>
        <button class="btn-ghost del" title="删除">🗑️</button>
      </div>`;
    if (!isDefault) {
      card.querySelector(".set-default").onclick = () => setDefaultModel(m.id);
    }
    card.querySelector(".edit").onclick = () => openModelModal(m.id);
    card.querySelector(".del").onclick = () => deleteModel(m.id);
    grid.appendChild(card);
  });
}

async function saveSettings(payload) {
  const res = await fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    currentSettings = await res.json();
    renderModelsGrid();
    return true;
  }
  alert("保存失败，请检查输入");
  return false;
}

async function setDefaultModel(id) {
  if (!currentSettings) return;
  await saveSettings({ ...currentSettings, default_model: id });
}

async function deleteModel(id) {
  if (!confirm("确定删除该模型？")) return;
  if (!currentSettings) return;
  const models = currentSettings.models.filter((m) => m.id !== id);
  const payload = {
    default_model: currentSettings.default_model === id ? (models[0] && models[0].id) || "" : currentSettings.default_model,
    models,
  };
  await saveSettings(payload);
}

function openModelModal(id) {
  editingModelId = id || null;
  $("#model-modal-title").textContent = id ? "编辑模型" : "添加模型";
  $("#m-id").value = id || "";
  if (id && currentSettings) {
    const m = currentSettings.models.find((x) => x.id === id);
    $("#m-name").value = m ? m.name || "" : "";
    $("#m-base_url").value = m ? m.base_url || "" : "";
    $("#m-api_key").value = m ? m.api_key || "" : "";
    $("#m-model_id").value = m ? m.model_id || "" : "";
  } else {
    $("#m-name").value = "";
    $("#m-base_url").value = "";
    $("#m-api_key").value = "";
    $("#m-model_id").value = "";
  }
  // 默认把 API Key 输入框重置为密码态
  $("#m-api_key").type = "password";
  $("#btn-toggle-m-key").textContent = "显示";
  $("#model-modal").classList.remove("hidden");
}

function closeModelModal() {
  $("#model-modal").classList.add("hidden");
  editingModelId = null;
}

async function saveModelFromModal() {
  const name = $("#m-name").value.trim();
  const base_url = $("#m-base_url").value.trim();
  const api_key = $("#m-api_key").value.trim();
  const model_id = $("#m-model_id").value.trim();
  if (!name || !base_url || !model_id) {
    return alert("请填写显示名称、接口地址和模型名称");
  }
  const models = (currentSettings && currentSettings.models) || [];
  let newModels;
  if (editingModelId) {
    newModels = models.map((m) =>
      m.id === editingModelId
        ? { ...m, name, base_url, api_key, model_id }
        : m
    );
  } else {
    const id = model_id.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-|-$/g, "") || "model";
    // 避免 id 冲突：若已有同名，加序号
    let uniqueId = id;
    let i = 1;
    while (newModels && newModels.some((m) => m.id === uniqueId)) {
      uniqueId = `${id}-${i}`;
      i++;
    }
    // 重新生成数组
    newModels = [...models, { id: uniqueId, name, base_url, api_key, model_id }];
  }
  const payload = {
    default_model: (currentSettings && currentSettings.default_model) || (newModels[0] && newModels[0].id) || "",
    models: newModels,
  };
  if (await saveSettings(payload)) {
    closeModelModal();
  }
}

function toggleModalKey() {
  const input = $("#m-api_key");
  const btn = $("#btn-toggle-m-key");
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "隐藏";
  } else {
    input.type = "password";
    btn.textContent = "显示";
  }
}

// 智能体编辑：模型下拉选项
async function populateModelSelect(selectedId) {
  let settings = currentSettings;
  if (!settings) {
    try {
      const res = await fetch("/api/settings");
      settings = await res.json();
    } catch (e) {
      settings = { models: [], default_model: "" };
    }
  }
  const sel = $("#f-model");
  sel.innerHTML = `<option value="">使用默认模型（${esc(settings.default_model || "未设置")}）</option>`;
  (settings.models || []).forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = `${esc(m.name)} (${esc(m.model_id)})`;
    if (m.id === selectedId) opt.selected = true;
    sel.appendChild(opt);
  });
}

// 打开修改（体验版只修改已有智能体）
async function openEdit(slug) {
  currentSlug = slug;
  $("#edit-title").textContent = "修改智能体";
  $("#f-slug").value = slug;
  const res = await fetch("/api/agents/" + slug);
  const a = await res.json();
  $("#f-name").value = a.name || "";
  $("#f-persona").value = a.persona || "";
  $("#f-description").value = a.description || "";
  $("#f-opening").value = a.opening || "";
  await populateModelSelect(a.model || "");
  // 知识库：单一文本框（优先字段，兼容旧文件回填）
  $("#f-knowledge-text").value = a.knowledge || "";
  $("#avatar-preview").textContent = "🙂";
  if (a.avatar) {
    $("#avatar-preview").innerHTML = `<img src="/data/agents/${a.slug}/${a.avatar}" />`;
  }
  showView("edit");
}

// 保存（一次性保存所有字段，含知识库文本框）
async function saveAgent() {
  const name = $("#f-name").value.trim();
  if (!name) return alert("请填写名称");
  const slug = $("#f-slug").value;
  if (!slug) return alert("请先打开一个智能体再保存");
  const payload = {
    name,
    persona: $("#f-persona").value,
    description: $("#f-description").value,
    opening: $("#f-opening").value,
    model: $("#f-model").value,
    knowledge: $("#f-knowledge-text").value,
  };
  await fetch("/api/agents/" + slug, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  // 头像上传（可选）
  const avFile = $("#f-avatar").files[0];
  if (avFile) {
    const fd = new FormData();
    fd.append("file", avFile);
    await fetch(`/api/agents/${slug}/avatar`, { method: "POST", body: fd });
  }
  alert("已保存");
  loadList();
  showView("list");
}

// 调试
function openDebug(slug) {
  currentSlug = slug;
  $("#debug-title").textContent = "调试 · " + slug;
  $("#debug-iframe").src = "/c/" + slug;
  const link = `${location.origin}/c/${slug}`;
  $("#debug-link").value = link;
  $("#share-row").style.display = "flex";
  showView("debug");
}

// 发布
async function publishAgent() {
  if (!currentSlug) return;
  const res = await fetch("/api/agents/" + currentSlug + "/publish", { method: "POST" });
  const r = await res.json();
  const link = `${location.origin}/c/${r.slug}`;
  $("#publish-link").value = link;
  $("#publish-modal").classList.remove("hidden");
  loadList();
}

// 健壮复制：clipboard API + 兜底 execCommand
async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (_) {}
    document.body.removeChild(ta);
  }
  if (btn) {
    const old = btn.textContent;
    btn.textContent = "已复制 ✓";
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = old; btn.classList.remove("copied"); }, 1500);
  }
}

// 删除
async function delAgent(slug) {
  if (!confirm("确定删除该智能体？")) return;
  await fetch("/api/agents/" + slug, { method: "DELETE" });
  loadList();
}

// 绑定
$$(".nav-item").forEach((n) => (n.onclick = () => {
  const view = n.dataset.view;
  if (view === "list") loadList();
  if (view === "settings") loadSettings();
  showView(view);
}));
$("#btn-cancel").onclick = () => { loadList(); showView("list"); };
$("#btn-save").onclick = saveAgent;
$("#btn-back-list").onclick = () => { loadList(); showView("list"); };
$("#btn-edit-from-debug").onclick = () => openEdit(currentSlug);
$("#btn-publish").onclick = publishAgent;
$("#btn-copy").onclick = () => copyText($("#publish-link").value, $("#btn-copy"));
$("#btn-close-modal").onclick = () => $("#publish-modal").classList.add("hidden");
$("#btn-copy-debug").onclick = () => copyText($("#debug-link").value, $("#btn-copy-debug"));

// 模型设置绑定
$("#btn-add-model").onclick = () => openModelModal();
$("#btn-cancel-model").onclick = closeModelModal;
$("#btn-save-model").onclick = saveModelFromModal;
$("#btn-toggle-m-key").onclick = toggleModalKey;

// 点击弹窗背景关闭
$("#model-modal").onclick = (e) => {
  if (e.target.id === "model-modal") closeModelModal();
};

// 初始
loadList();
