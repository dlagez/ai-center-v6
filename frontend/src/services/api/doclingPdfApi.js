import { buildApiUrl, parseJsonResponse } from "./client";

export async function parseDoclingPdf(fileId) {
  const response = await fetch(buildApiUrl("/api/docling/pdf/parse"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ file_id: fileId }),
  });

  return parseJsonResponse(response);
}
