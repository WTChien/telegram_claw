import { api } from "./api.js";
import { ServiceManager } from "./service-manager.js";
import { fmtJson, ts } from "./utils.js";

const userId = localStorage.getItem("nanoclaw.userId") || "web-user";
const manager = new ServiceManager(userId);

const serviceCards = document.getElementById("serviceCards");
const scanBtn = document.getElementById("scanBtn");
const currentServiceText = document.getElementById("currentServiceText");
const logBox = document.getElementById("logBox");
const sendChatBtn = document.getElementById("sendChatBtn");
const chatModel = document.getElementById("chatModel");
const chatMessage = document.getElementById("chatMessage");
const chatOutput = document.getElementById("chatOutput");
const loadModelsBtn = document.getElementById("loadModelsBtn");
const modelsList = document.getElementById("modelsList");

function log(message, level = "info") {
  const line = document.createElement("div");
  line.textContent = `[${ts()}] ${message}`;
  if (level === "error") {
    line.style.color = "#8f2f28";
  }
  logBox.prepend(line);
}

function renderServices(services) {
  serviceCards.innerHTML = "";
  if (!services.length) {
    serviceCards.innerHTML = "<p>沒有找到服務，請嘗試掃描。</p>";
    return;
  }

  for (const svc of services) {
    const card = document.createElement("article");
    card.className = "service-card";
    card.innerHTML = `
      <div class="name">${svc.name}</div>
      <div class="meta">${svc.host}:${svc.port}</div>
      <div class="meta">${svc.description || "No description"}</div>
      <div class="status ${svc.status}">${svc.status}</div>
      <button class="btn" ${svc.status !== "running" ? "disabled" : ""}>連接</button>
    `;

    const button = card.querySelector("button");
    button.addEventListener("click", async () => {
      try {
        await manager.connect(svc.port);
        await manager.savePreference(svc.port, svc.name);
        currentServiceText.textContent = `${svc.name} (${svc.port})`;
        log(`已連接到 ${svc.name}:${svc.port}`);
      } catch (err) {
        log(`連接失敗: ${err.message}`, "error");
      }
    });

    serviceCards.appendChild(card);
  }
}

async function scanAndRender() {
  scanBtn.disabled = true;
  try {
    const services = await manager.scan();
    renderServices(services);
    log(`掃描完成，共 ${services.length} 個服務`);
  } catch (err) {
    log(`掃描失敗: ${err.message}`, "error");
  } finally {
    scanBtn.disabled = false;
  }
}

async function loadCurrent() {
  try {
    const current = await manager.current();
    const conn = current.connection;
    currentServiceText.textContent = `${conn.service_name} (${conn.port}) | 已轉發 ${conn.requests_count} 次`;
  } catch (_err) {
    currentServiceText.textContent = "尚未連接服務";
  }
}

scanBtn.addEventListener("click", scanAndRender);

sendChatBtn.addEventListener("click", async () => {
  const message = chatMessage.value.trim();
  if (!message) {
    return;
  }

  sendChatBtn.disabled = true;
  try {
    const result = await api.chatMessage(userId, message, chatModel.value.trim());
    chatOutput.textContent = fmtJson(result.response);
    log("訊息已轉發到當前服務");
    chatMessage.value = "";
    await loadCurrent();
  } catch (err) {
    chatOutput.textContent = err.message;
    log(`聊天失敗: ${err.message}`, "error");
  } finally {
    sendChatBtn.disabled = false;
  }
});

loadModelsBtn.addEventListener("click", async () => {
  loadModelsBtn.disabled = true;
  try {
    const data = await api.getModels(userId);
    modelsList.innerHTML = "";
    for (const model of data.models || []) {
      const item = document.createElement("li");
      item.textContent = model;
      modelsList.appendChild(item);
    }
    if (!data.models || !data.models.length) {
      modelsList.innerHTML = "<li>沒有可用模型</li>";
    }
    log("模型列表已更新");
  } catch (err) {
    log(`載入模型失敗: ${err.message}`, "error");
  } finally {
    loadModelsBtn.disabled = false;
  }
});

(async function boot() {
  await loadCurrent();
  await scanAndRender();
})();
