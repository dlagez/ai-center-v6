async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function listDoclingTasks({ fileId, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (fileId) {
    params.set("file_id", fileId);
  }
  params.set("limit", String(limit));
  const response = await fetch(`/api/docling/pdf/tasks?${params.toString()}`);
  return parseJsonResponse(response);
}

export async function getDoclingTaskDetail(taskId) {
  const response = await fetch(`/api/docling/pdf/tasks/${taskId}`);
  return parseJsonResponse(response);
}
