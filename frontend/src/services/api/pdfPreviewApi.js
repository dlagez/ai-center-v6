async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function uploadPdfFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("biz_type", "pdf-preview");

  const response = await fetch("/files/upload", {
    method: "POST",
    body: formData,
  });

  return parseJsonResponse(response);
}

export async function listPdfPreviewFiles() {
  const response = await fetch("/api/pdf-preview/files");
  return parseJsonResponse(response);
}

export function getPdfPreviewFileUrl(fileId) {
  return `/api/pdf-preview/files/${fileId}/file`;
}
