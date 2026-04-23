import { buildApiUrl, parseJsonResponse } from "./client";

export async function listKnowledgeBases() {
  const response = await fetch(buildApiUrl("/api/knowledge/bases"));
  return parseJsonResponse(response);
}

export async function createKnowledgeBase(payload) {
  const response = await fetch(buildApiUrl("/api/knowledge/bases"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function updateKnowledgeBase(kbId, payload) {
  const response = await fetch(buildApiUrl(`/api/knowledge/bases/${kbId}`), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function deleteKnowledgeBase(kbId) {
  const response = await fetch(buildApiUrl(`/api/knowledge/bases/${kbId}`), {
    method: "DELETE",
  });
  return parseJsonResponse(response);
}

export async function getKnowledgeBaseStats(kbId) {
  const response = await fetch(buildApiUrl(`/api/knowledge/bases/${kbId}/stats`));
  return parseJsonResponse(response);
}

export async function listKnowledgeDocuments(kbId, limit = 500) {
  const response = await fetch(buildApiUrl(`/api/knowledge/bases/${kbId}/documents?limit=${limit}`));
  return parseJsonResponse(response);
}

export async function listKnowledgeFiles() {
  const response = await fetch(buildApiUrl("/api/knowledge/files"));
  return parseJsonResponse(response);
}

export async function searchKnowledge(kbId, { query, fileId, chunkerType, limit = 5 }) {
  const response = await fetch(buildApiUrl(`/api/knowledge/bases/${kbId}/search`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      file_id: fileId || null,
      chunker_type: chunkerType || null,
      limit,
    }),
  });
  return parseJsonResponse(response);
}

export async function deleteKnowledgeDocument(kbId, { fileId, chunkerType }) {
  const params = new URLSearchParams();
  if (chunkerType) {
    params.set("chunker_type", chunkerType);
  }
  const response = await fetch(
    buildApiUrl(`/api/knowledge/bases/${kbId}/documents/${fileId}?${params.toString()}`),
    {
      method: "DELETE",
    },
  );
  return parseJsonResponse(response);
}
