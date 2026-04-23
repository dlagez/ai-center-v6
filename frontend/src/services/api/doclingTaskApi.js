import { buildApiUrl, parseJsonResponse } from "./client";

export async function listDoclingTasks({ fileId, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (fileId) {
    params.set("file_id", fileId);
  }
  params.set("limit", String(limit));
  const response = await fetch(buildApiUrl(`/api/docling/pdf/tasks?${params.toString()}`));
  return parseJsonResponse(response);
}

export async function getDoclingTaskDetail(taskId) {
  const response = await fetch(buildApiUrl(`/api/docling/pdf/tasks/${taskId}`));
  return parseJsonResponse(response);
}
