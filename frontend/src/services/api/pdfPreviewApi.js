import { buildApiUrl, parseJsonResponse } from "./client";

export async function uploadPdfFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("biz_type", "pdf-preview");

  const response = await fetch(buildApiUrl("/files/upload"), {
    method: "POST",
    body: formData,
  });

  return parseJsonResponse(response);
}

export async function listPdfPreviewFiles() {
  const response = await fetch(buildApiUrl("/api/pdf-preview/files"));
  return parseJsonResponse(response);
}

export function getPdfPreviewFileUrl(fileId) {
  return buildApiUrl(`/api/pdf-preview/files/${fileId}/file`);
}
