const API_PORT = "8000";

function getApiOrigin() {
  if (typeof window === "undefined") {
    return `http://127.0.0.1:${API_PORT}`;
  }
  const host = window.location.hostname || "127.0.0.1";
  return `http://${host}:${API_PORT}`;
}

export function buildApiUrl(path) {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  return `${getApiOrigin()}${path}`;
}

export async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}
