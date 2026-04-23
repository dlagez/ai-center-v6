import { useEffect, useState } from "react";

import { createKnowledgeBase, listKnowledgeBases } from "../../services/api/knowledgeApi";
import "./styles.css";

const INITIAL_FORM = {
  name: "",
  description: "",
  bizType: "general",
  chunkerType: "default",
};

function formatUpdatedTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function KnowledgeBasePage() {
  const [bases, setBases] = useState([]);
  const [form, setForm] = useState(INITIAL_FORM);
  const [status, setStatus] = useState("正在加载知识库列表...");
  const [isCreating, setIsCreating] = useState(false);

  const refreshBases = async () => {
    const nextBases = await listKnowledgeBases();
    setBases(nextBases);
    setStatus("知识库列表已加载。");
  };

  useEffect(() => {
    refreshBases().catch((error) => {
      setStatus(error instanceof Error ? error.message : "加载知识库列表失败");
    });
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setStatus("请输入知识库名称。");
      return;
    }
    try {
      setIsCreating(true);
      setStatus("正在创建知识库...");
      const payload = await createKnowledgeBase({
        name: form.name.trim(),
        description: form.description.trim() || null,
        biz_type: form.bizType.trim() || "general",
        chunker_type: form.chunkerType,
      });
      window.location.href = `/knowledge-base/detail?kb_id=${payload.kb_id}`;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "创建知识库失败");
    } finally {
      setIsCreating(false);
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
          <span className="kb-global-current">Knowledge</span>
        </div>
        <div className="kb-global-actions">
          <a className="kb-ghost-link" href="/pdf-preview">
            Preview
          </a>
        </div>
      </header>

      <section className="kb-list-toolbar">
        <div>
          <p className="kb-hero-label">Knowledge</p>
          <h1>知识库列表</h1>
          <p className="kb-hero-text">每个知识库独立维护一个 collection，用于文档入库、检索测试和后续问答配置。</p>
        </div>
        <div className="kb-list-meta">
          <span>{bases.length} 个知识库</span>
          <button className="kb-ghost-button" onClick={() => refreshBases()} type="button">
            刷新
          </button>
        </div>
      </section>

      <section className="kb-status-inline">{status}</section>

      <section className="kb-list-grid">
        <article className="kb-create-card">
          <div className="kb-create-card-head">
            <strong>Create Knowledge</strong>
            <span>新建一个独立知识库空间</span>
          </div>
          <form className="kb-create-form" onSubmit={handleCreate}>
            <label className="kb-input-group">
              <span>名称</span>
              <input
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="例如：资格预审知识库"
                value={form.name}
              />
            </label>
            <label className="kb-input-group">
              <span>业务类型</span>
              <input
                onChange={(event) => setForm((current) => ({ ...current, bizType: event.target.value }))}
                placeholder="例如：tender"
                value={form.bizType}
              />
            </label>
            <label className="kb-input-group">
              <span>默认 Chunker</span>
              <select
                onChange={(event) => setForm((current) => ({ ...current, chunkerType: event.target.value }))}
                value={form.chunkerType}
              >
                <option value="default">默认 Chunker</option>
                <option value="tender">招投标专用 Chunker</option>
              </select>
            </label>
            <label className="kb-input-group">
              <span>描述</span>
              <textarea
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="说明这个知识库的使用范围"
                rows="5"
                value={form.description}
              />
            </label>
            <button className="kb-primary-button" disabled={isCreating} type="submit">
              {isCreating ? "创建中..." : "Create Knowledge"}
            </button>
          </form>
        </article>

        {bases.map((base) => (
          <a className="kb-list-card" href={`/knowledge-base/detail?kb_id=${base.kb_id}`} key={base.kb_id}>
            <div className="kb-list-card-head">
              <div className="kb-list-icon" aria-hidden="true">
                KB
              </div>
              <div className="kb-list-card-title">
                <strong>{base.name}</strong>
                <span>{base.biz_type}</span>
              </div>
            </div>
            <div className="kb-list-card-tags">
              <span>{base.chunker_type === "tender" ? "TENDER" : "GENERAL"}</span>
              <span>QDRANT</span>
              <span>{base.status.toUpperCase()}</span>
            </div>
            <p className="kb-list-card-desc">{base.description || "未填写描述。"}</p>
            <div className="kb-list-card-footer">
              <span>{base.document_count} 文档</span>
              <span>{base.chunk_count} chunks</span>
              <span>{formatUpdatedTime(base.updated_at)}</span>
            </div>
          </a>
        ))}
      </section>
    </main>
  );
}
