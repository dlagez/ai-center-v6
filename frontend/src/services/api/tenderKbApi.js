import { buildApiUrl, parseJsonResponse } from "./client";

export async function indexTenderKb(fileId) {
  const response = await fetch(buildApiUrl("/api/tender-kb/index"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ file_id: fileId }),
  });
  return parseJsonResponse(response);
}

export async function askTenderKb({ fileId, question, limit = 5 }) {
  const response = await fetch(buildApiUrl("/api/tender-kb/ask"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      file_id: fileId,
      question,
      limit,
    }),
  });
  return parseJsonResponse(response);
}
