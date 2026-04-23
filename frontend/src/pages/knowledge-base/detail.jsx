import { useEffect, useMemo, useState } from "react";

import {
  deleteKnowledgeBase,
  deleteKnowledgeDocument,
  getKnowledgeBaseStats,
  indexKnowledgeDocument,
  listKnowledgeDocuments,
  listKnowledgeFiles,
  searchKnowledge,
} from "../../services/api/knowledgeApi";
import "./styles.css";

function getKbId() {
  return new URLSearchParams(window.location.search).get("kb_id") || "";
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getChunkLabel(value) {
  return value === "tender" ? "PARENT-CHILD / TENDER" : "GENERAL / DEFAULT";
}

function getDocumentStatusLabel(document) {
  if (document.status === "failed") {
    return "Failed";
  }
  if (document.status === "running") {
    return `Running / ${document.current_stage || "-"}`;
  }
  return "Available";
}

export default function KnowledgeBaseDetailPage() {
  const kbId = getKbId();
  const [base, setBase] = useState(null);
  const [files, setFiles] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState("documents");
  const [selectedFileId, setSelectedFileId] = useState("");
  const [selectedDocumentKey, setSelectedDocumentKey] = useState("");
  const [question, setQuestion] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [status, setStatus] = useState("正在加载知识库详情...");
  const [isIndexing, setIsIndexing] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  const selectedDocument = useMemo(
    () => documents.find((doc) => `${doc.file_id}:${doc.chunker}` === selectedDocumentKey) || null,
    [documents, selectedDocumentKey],
  );

  const refreshBase = async () => {
    if (!kbId) {
      throw new Error("缺少 kb_id");
    }
    const [nextBase, nextDocuments, nextFiles] = await Promise.all([
      getKnowledgeBaseStats(kbId),
      listKnowledgeDocuments(kbId),
      listKnowledgeFiles(),
    ]);
    setBase(nextBase);
    setDocuments(nextDocuments);
    setFiles(nextFiles);
    setSelectedFileId((current) => current || nextFiles[0]?.file_id || "");
    setSelectedDocumentKey((current) => {
      if (current && nextDocuments.some((doc) => `${doc.file_id}:${doc.chunker}` === current)) {
        return current;
      }
      return nextDocuments[0] ? `${nextDocuments[0].file_id}:${nextDocuments[0].chunker}` : "";
    });
  };

  useEffect(() => {
    refreshBase()
      .then(() => setStatus("知识库详情已加载。"))
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "加载知识库详情失败");
      });
  }, [kbId]);

  const handleDeleteBase = async () => {
    if (!base) {
      return;
    }
    try {
      setStatus(`正在删除知识库 ${base.name}...`);
      await deleteKnowledgeBase(base.kb_id);
      window.location.href = "/knowledge-base";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除知识库失败");
    }
  };

  const handleIndex = async () => {
    if (!base) {
      setStatus("知识库未加载完成。");
      return;
    }
    if (!selectedFileId) {
      setStatus("请选择一个文件。");
      return;
    }
    try {
      setIsIndexing(true);
      setStatus(`正在向 ${base.name} 入库...`);
      const payload = await indexKnowledgeDocument(base.kb_id, {
        fileId: selectedFileId,
        chunkerType: base.chunker_type,
      });
      await refreshBase();
      setSelectedDocumentKey(`${payload.file_id}:${payload.chunker}`);
      setStatus(`入库完成：${payload.file_name}，共 ${payload.chunk_count} 个 chunks。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "入库失败");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleDeleteDocument = async (document) => {
    if (!base) {
      return;
    }
    try {
      setStatus(`正在删除文档 ${document.file_name}...`);
      await deleteKnowledgeDocument(base.kb_id, {
        fileId: document.file_id,
        chunkerType: document.chunker,
      });
      await refreshBase();
      setSearchResult(null);
      setStatus("文档已移出当前知识库。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除文档失败");
    }
  };

  const handleRetryDocument = async (document) => {
    if (!base) {
      return;
    }
    try {
      setIsIndexing(true);
      setStatus(`正在重试 ${document.file_name} 的入库...`);
      const payload = await indexKnowledgeDocument(base.kb_id, {
        fileId: document.file_id,
        chunkerType: document.chunker,
      });
      await refreshBase();
      setSelectedDocumentKey(`${payload.file_id}:${payload.chunker}`);
      setStatus(`重试成功：${payload.file_name}，共 ${payload.chunk_count} 个 chunks。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "重试失败");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleSearch = async (event) => {
    event.preventDefault();
    if (!base) {
      setStatus("知识库未加载完成。");
      return;
    }
    if (!question.trim()) {
      setStatus("请输入检索问题。");
      return;
    }
    try {
      setIsSearching(true);
      setStatus(`正在 ${base.name} 中检索...`);
      const payload = await searchKnowledge(base.kb_id, {
        query: question,
        fileId: selectedDocument?.file_id || "",
        chunkerType: selectedDocument?.chunker || "",
        limit: 8,
      });
      setSearchResult(payload);
      setStatus(`检索完成，共命中 ${payload.results.length} 条。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "检索失败");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <main className="kb-page kb-page-dark">
      <header className="kb-global-header">
        <div className="kb-global-brand">
          <a className="kb-brand-link" href="/">
            AI Center
          </a>
          <span className="kb-global-sep">/</span>
          <a className="kb-brand-link" href="/knowledge-base">
            Knowledge
          </a>
          <span className="kb-global-sep">/</span>
          <span className="kb-global-current">{base?.name || "Detail"}</span>
        </div>
        <div className="kb-global-actions">
          <button className="kb-ghost-button" onClick={() => refreshBase()} type="button">
            Refresh
          </button>
          <button className="kb-danger-button" onClick={handleDeleteBase} type="button">
            删除知识库
          </button>
        </div>
      </header>

      <section className="kb-status-inline">{status}</section>

      <section className="kb-detail-layout">
        <aside className="kb-detail-sidebar">
          <div className="kb-sidebar-brand">
            <div className="kb-detail-avatar">KB</div>
            <div>
              <strong>{base?.name || "Knowledge Base"}</strong>
              <span>{base?.biz_type || "-"}</span>
            </div>
          </div>

          <div className="kb-sidebar-meta">
            <span>{base?.document_count ?? 0} documents</span>
            <span>{base?.chunk_count ?? 0} chunks</span>
            <span>{base?.collection_name || "-"}</span>
            <span>{getChunkLabel(base?.chunker_type)}</span>
          </div>

          <nav className="kb-detail-nav">
            <button
              className={activeTab === "documents" ? "is-active" : ""}
              onClick={() => setActiveTab("documents")}
              type="button"
            >
              Documents
            </button>
            <button
              className={activeTab === "retrieval" ? "is-active" : ""}
              onClick={() => setActiveTab("retrieval")}
              type="button"
            >
              Retrieval Testing
            </button>
          </nav>

          <a className="kb-sidebar-back" href="/knowledge-base">
            返回知识库列表
          </a>
        </aside>

        <section className="kb-detail-main">
          {activeTab === "documents" ? (
            <>
              <header className="kb-section-head">
                <div>
                  <h1>Documents</h1>
                  <p>当前知识库中的文件列表、入库操作和基础状态都在这里统一查看。</p>
                </div>
                <div className="kb-section-actions">
                  <button className="kb-ghost-button" type="button">
                    Metadata
                  </button>
                  <button className="kb-primary-button" disabled={!selectedFileId || isIndexing} onClick={handleIndex} type="button">
                    {isIndexing ? "入库中..." : "Add file"}
                  </button>
                </div>
              </header>

              <section className="kb-detail-toolbar">
                <select onChange={(event) => setSelectedFileId(event.target.value)} value={selectedFileId}>
                  <option value="">选择一个 PDF 文件</option>
                  {files.map((file) => (
                    <option key={file.file_id} value={file.file_id}>
                      {file.file_name}
                    </option>
                  ))}
                </select>
                <div className="kb-detail-toolbar-pill">{base ? getChunkLabel(base.chunker_type) : "-"}</div>
                <div className="kb-detail-toolbar-pill">{documents.length} Files</div>
              </section>

              <section className="kb-documents-table-shell">
                <div className="kb-documents-head">
                  <span>#</span>
                  <span>NAME</span>
                  <span>CHUNKING MODE</span>
                  <span>WORDS</span>
                  <span>UPLOAD TIME</span>
                  <span>STATUS</span>
                  <span>ACTION</span>
                </div>
                <div className="kb-documents-body">
                  {documents.length ? (
                    documents.map((document, index) => (
                      <article
                        className={`kb-document-row ${selectedDocumentKey === `${document.file_id}:${document.chunker}` ? "is-active" : ""}`}
                        key={`${document.file_id}:${document.chunker}`}
                      >
                        <button
                          className="kb-document-select"
                          onClick={() => setSelectedDocumentKey(`${document.file_id}:${document.chunker}`)}
                          type="button"
                        >
                          <span>{index + 1}</span>
                          <span className="kb-document-name">
                            <strong>{document.file_name}</strong>
                            <em>{document.folder_path || "未记录目录"}</em>
                          </span>
                          <span>{getChunkLabel(document.chunker)}</span>
                          <span>{document.chunk_count || "-"}</span>
                          <span>{formatTime(document.updated_at)}</span>
                          <span className={document.status === "failed" ? "kb-status-failed" : "kb-status-ok"}>
                            {getDocumentStatusLabel(document)}
                          </span>
                        </button>
                        <div className="kb-row-actions">
                          {document.status === "failed" ? (
                            <button className="kb-row-retry" onClick={() => handleRetryDocument(document)} type="button">
                              重试
                            </button>
                          ) : null}
                          <button className="kb-row-action" onClick={() => handleDeleteDocument(document)} type="button">
                            删除
                          </button>
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="kb-empty-state">当前知识库还没有文档，先从上方选择文件并入库。</div>
                  )}
                </div>
              </section>

              {selectedDocument ? (
                <section className="kb-current-box">
                  <strong>当前文档状态</strong>
                  <pre>{JSON.stringify({
                    file_name: selectedDocument.file_name,
                    status: selectedDocument.status,
                    current_stage: selectedDocument.current_stage,
                    last_error_stage: selectedDocument.last_error_stage,
                    retry_count: selectedDocument.retry_count,
                    parse_task_id: selectedDocument.parse_task_id,
                    error_message: selectedDocument.error_message,
                    last_index_started_at: selectedDocument.last_index_started_at,
                    last_index_finished_at: selectedDocument.last_index_finished_at,
                    last_retry_at: selectedDocument.last_retry_at,
                    indexed_at: selectedDocument.indexed_at,
                  }, null, 2)}</pre>
                </section>
              ) : null}
            </>
          ) : (
            <>
              <header className="kb-section-head">
                <div>
                  <h1>Retrieval Testing</h1>
                  <p>在当前知识库内做检索测试，支持限定到某个文件，用来调试 chunk 和召回质量。</p>
                </div>
              </header>

              <section className="kb-retrieval-controls">
                <div className="kb-current-chip">
                  <span>当前知识库</span>
                  <strong>{base?.name || "-"}</strong>
                </div>
                <div className="kb-current-chip">
                  <span>限定文档</span>
                  <strong>{selectedDocument?.file_name || "全库"}</strong>
                </div>
              </section>

              <form className="kb-retrieval-form" onSubmit={handleSearch}>
                <textarea
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="例如：资格预审文件要求提供哪些法定代表人相关材料？"
                  rows="6"
                  value={question}
                />
                <button className="kb-primary-button" disabled={isSearching} type="submit">
                  {isSearching ? "检索中..." : "Run Retrieval Test"}
                </button>
              </form>

              <section className="kb-retrieval-results">
                {searchResult?.results?.length ? (
                  searchResult.results.map((item) => (
                    <article className="kb-retrieval-card" key={item.id}>
                      <div className="kb-retrieval-card-head">
                        <strong>{item.metadata?.heading || "未命名片段"}</strong>
                        <span>{item.score.toFixed(3)}</span>
                      </div>
                      <div className="kb-retrieval-meta">
                        <span>文件: {item.metadata?.file_name || "-"}</span>
                        <span>页码: {(item.metadata?.page_nos || []).join(", ") || "-"}</span>
                        <span>Chunker: {item.metadata?.chunker || "-"}</span>
                      </div>
                      <p>{item.text}</p>
                    </article>
                  ))
                ) : (
                  <div className="kb-empty-state">这里会展示当前知识库的检索结果。</div>
                )}
              </section>
            </>
          )}
        </section>
      </section>
    </main>
  );
}
