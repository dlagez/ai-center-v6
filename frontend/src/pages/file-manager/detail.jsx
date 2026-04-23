import { useEffect, useMemo, useState } from "react";

import { getManagedFileDetail } from "../../services/api/fileManagerApi";
import "./styles.css";

function getFileId() {
  return new URLSearchParams(window.location.search).get("file_id") || "";
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
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFileSize(size) {
  if (!size) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export default function FileManagerDetailPage() {
  const fileId = getFileId();
  const [detail, setDetail] = useState(null);
  const [status, setStatus] = useState("正在加载文件详情...");
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [selectedBatchNo, setSelectedBatchNo] = useState("");

  const groupedPageResults = useMemo(() => {
    const groups = new Map();
    for (const item of detail?.page_results || []) {
      const key = String(item.batch_no);
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(item);
    }
    return Array.from(groups.entries()).map(([batchNo, items]) => {
      const sortedItems = [...items].sort((a, b) => a.page_no - b.page_no);
      const firstMarkdownItem = sortedItems.find((item) => item.markdown);
      return {
        batchNo,
        items: sortedItems,
        markdown: firstMarkdownItem?.markdown || "",
        pageStart: sortedItems[0]?.page_no || 0,
        pageEnd: sortedItems[sortedItems.length - 1]?.page_no || 0,
      };
    });
  }, [detail]);

  const selectedBatch = useMemo(
    () => groupedPageResults.find((item) => item.batchNo === selectedBatchNo) || groupedPageResults[0] || null,
    [groupedPageResults, selectedBatchNo],
  );

  const loadDetail = async (taskId = selectedTaskId) => {
    if (!fileId) {
      throw new Error("缺少 file_id");
    }
    const payload = await getManagedFileDetail(fileId, { taskId });
    setDetail(payload);
    setSelectedTaskId(payload.selected_task?.task_id || "");
    const groups = new Map();
    for (const item of payload.page_results || []) {
      groups.set(String(item.batch_no), true);
    }
    setSelectedBatchNo((current) => (current && groups.has(current) ? current : Array.from(groups.keys())[0] || ""));
    setStatus("文件详情已加载。");
  };

  useEffect(() => {
    loadDetail().catch((error) => {
      setStatus(error instanceof Error ? error.message : "加载文件详情失败");
    });
  }, [fileId]);

  const handleTaskChange = async (event) => {
    const nextTaskId = event.target.value;
    setSelectedTaskId(nextTaskId);
    try {
      setStatus("正在切换解析任务...");
      await loadDetail(nextTaskId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "切换任务失败");
    }
  };

  return (
    <main className="file-manager-shell">
      <header className="file-manager-hero">
        <div>
          <p className="file-manager-eyebrow">File Detail</p>
          <h1>文件详情</h1>
          <p className="file-manager-lead">查看文件基础信息、Docling 解析任务进度、每页解析结果，以及原始 JSON / Markdown。</p>
        </div>
        <a className="file-manager-back" href="/file-manager">
          返回文件列表
        </a>
      </header>

      <section className="file-manager-status">{status}</section>

      {detail ? (
        <>
          <section className="file-detail-summary-grid">
            <article className="file-detail-card">
              <span>文件名</span>
              <strong>{detail.file.file_name}</strong>
              <small>{detail.file.object_name}</small>
            </article>
            <article className="file-detail-card">
              <span>业务类型</span>
              <strong>{detail.file.biz_type}</strong>
              <small>{detail.file.folder_path}</small>
            </article>
            <article className="file-detail-card">
              <span>文件大小</span>
              <strong>{formatFileSize(detail.file.file_size)}</strong>
              <small>{detail.file.content_type}</small>
            </article>
            <article className="file-detail-card">
              <span>上传时间</span>
              <strong>{formatTime(detail.file.created_at)}</strong>
              <small>{detail.parse_tasks.length} 个解析任务</small>
            </article>
          </section>

          <section className="file-manager-toolbar">
            <div className="file-manager-filter-box">
              <label className="file-manager-field">
                <span>解析任务</span>
                <select onChange={handleTaskChange} value={selectedTaskId}>
                  {detail.parse_tasks.map((task) => (
                    <option key={task.task_id} value={task.task_id}>
                      {task.task_id} / {task.status}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          {detail.selected_task ? (
            <section className="file-detail-task-grid">
              <article className="file-detail-panel">
                <h2>解析任务状态</h2>
                <pre>{JSON.stringify(detail.selected_task, null, 2)}</pre>
              </article>
              <article className="file-detail-panel">
                <h2>批次结果列表</h2>
                <div className="file-detail-page-list">
                  {groupedPageResults.length ? (
                    groupedPageResults.map((group) => (
                      <button
                        className={`file-detail-page-item ${selectedBatch?.batchNo === group.batchNo ? "is-active" : ""}`}
                        key={group.batchNo}
                        onClick={() => setSelectedBatchNo(group.batchNo)}
                        type="button"
                      >
                        <strong>批次 {group.batchNo}</strong>
                        <span>页范围: {group.pageStart} - {group.pageEnd}</span>
                        <span>页数: {group.items.length}</span>
                        <span>markdown: {group.markdown ? "有" : "无"}</span>
                        <span>json: {group.items.length} 个</span>
                      </button>
                    ))
                  ) : (
                    <div className="file-manager-empty">当前任务还没有页结果。</div>
                  )}
                </div>
              </article>
            </section>
          ) : null}

          {selectedBatch ? (
            <section className="file-detail-result-grid">
              <article className="file-detail-panel">
                <h2>批次 Markdown</h2>
                <pre>{selectedBatch.markdown || ""}</pre>
              </article>
              <article className="file-detail-panel">
                <h2>批次 JSON 列表</h2>
                <div className="file-detail-json-list">
                  {selectedBatch.items.map((item) => (
                    <section className="file-detail-json-item" key={item.result_id}>
                      <div className="file-detail-json-head">
                        <strong>第 {item.page_no} 页</strong>
                        <span>blocks: {item.block_count}</span>
                      </div>
                      <pre>{JSON.stringify(item.result_json || {}, null, 2)}</pre>
                    </section>
                  ))}
                </div>
              </article>
            </section>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
