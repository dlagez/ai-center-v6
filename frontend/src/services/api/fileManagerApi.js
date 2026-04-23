import { buildApiUrl, parseJsonResponse } from "./client";

export async function listManagedFiles({ bizType = "", limit = 500 } = {}) {
  const params = new URLSearchParams();
  if (bizType) {
    params.set("biz_type", bizType);
  }
  params.set("limit", String(limit));
  const response = await fetch(buildApiUrl(`/api/files?${params.toString()}`));
  return parseJsonResponse(response);
}

export async function uploadManagedFile(file, { bizType = "general", bizId = "" } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("biz_type", bizType);
  if (bizId) {
    formData.append("biz_id", bizId);
  }

  const response = await fetch(buildApiUrl("/files/upload"), {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse(response);
}

export async function deleteManagedFile(fileId) {
  const response = await fetch(buildApiUrl(`/api/files/${fileId}`), {
    method: "DELETE",
  });
  return parseJsonResponse(response);
}

export async function getManagedFileDetail(fileId, { taskId = "" } = {}) {
  const params = new URLSearchParams();
  if (taskId) {
    params.set("task_id", taskId);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(buildApiUrl(`/api/files/${fileId}${suffix}`));
  return parseJsonResponse(response);
}
