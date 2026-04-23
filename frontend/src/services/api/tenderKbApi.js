async function parseJsonResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

export async function indexTenderKb(fileId) {
  const response = await fetch("/api/tender-kb/index", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ file_id: fileId }),
  });
  return parseJsonResponse(response);
}

export async function askTenderKb({ fileId, question, limit = 5 }) {
  const response = await fetch("/api/tender-kb/ask", {
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
