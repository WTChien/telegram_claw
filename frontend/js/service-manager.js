import { api } from "./api.js";

export class ServiceManager {
  constructor(userId) {
    this.userId = userId;
    this.services = [];
  }

  async scan() {
    const data = await api.scanServices();
    this.services = data.services || [];
    return this.services;
  }

  async connect(port) {
    return api.connectService(this.userId, port);
  }

  async current() {
    return api.getCurrent(this.userId);
  }

  async savePreference(port, name) {
    return api.savePreference(this.userId, port, name);
  }
}
