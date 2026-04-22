async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function listExcelUpdateTasks() {
  const response = await fetch("/workflow/excel-update/tasks");
  return parseJsonResponse(response);
}

export async function createExcelUpdateTask(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/workflow/excel-update/tasks", {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse(response);
}

export async function getExcelUpdateTask(taskId) {
  const response = await fetch(`/workflow/excel-update/tasks/${encodeURIComponent(taskId)}`);
  return parseJsonResponse(response);
}

export async function createExcelUpdateOperation(taskId, payload) {
  const formData = new FormData();
  formData.append("source_type", payload.sourceType);
  formData.append("user_prompt", payload.userPrompt);
  if (payload.sourceType === "excel_file" && payload.sourceFile) {
    formData.append("source_file", payload.sourceFile);
  }

  const response = await fetch(
    `/workflow/excel-update/tasks/${encodeURIComponent(taskId)}/operations`,
    {
      method: "POST",
      body: formData,
    },
  );
  return parseJsonResponse(response);
}
