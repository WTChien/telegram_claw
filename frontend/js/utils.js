export function fmtJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch (_err) {
    return String(value);
  }
}

export function ts() {
  return new Date().toLocaleTimeString();
}
