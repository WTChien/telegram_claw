const API_BASE = "";

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await resp.text();
  const body = text ? JSON.parse(text) : {};

  if (!resp.ok) {
    const message = body.detail || body.error || `Request failed: ${resp.status}`;
    throw new Error(message);
  }

  return body;
}

export const api = {
  scanServices() {
    return request("/api/services/scan");
  },
  connectService(userId, port) {
    return request("/api/services/connect", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, port }),
    });
  },
  getCurrent(userId) {
    return request(`/api/services/current?user_id=${encodeURIComponent(userId)}`);
  },
  savePreference(userId, preferredPort, preferredService) {
    return request("/api/services/user/preference", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        preferred_port: preferredPort,
        preferred_service: preferredService,
      }),
    });
  },
  getModels(userId) {
    return request(`/api/chat/models?user_id=${encodeURIComponent(userId)}`);
  },
  chatMessage(userId, message, model) {
    return request("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        message,
        model: model || null,
      }),
    });
  },
};
