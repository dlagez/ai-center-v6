const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function getApiBaseUrl() {
  const value = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function buildApiUrl(path) {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  return `${getApiBaseUrl()}${path}`;
}

export async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}
