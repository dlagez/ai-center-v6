import { useEffect, useState } from "react";

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

  useEffect(() => {
    if (!fileId) {
      setStatus("缺少 file_id");
      return;
    }
    getManagedFileDetail(fileId)
      .then((payload) => {
        setDetail(payload);
        setStatus("文件详情已加载。");
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "加载文件详情失败");
      });
  }, [fileId]);

  return (
    <main className="file-manager-shell">
      <header className="file-manager-hero">
        <div>
          <p className="file-manager-eyebrow">File Detail</p>
          <h1>文件详情</h1>
          <p className="file-manager-lead">仅保留文件元信息查看，不再展示 parser 相关任务和结果。</p>
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
              <small>{detail.file.bucket_name}</small>
            </article>
          </section>

          <section className="file-detail-result-grid">
            <article className="file-detail-panel">
              <h2>文件元信息</h2>
              <pre>{JSON.stringify(detail.file, null, 2)}</pre>
            </article>
          </section>
        </>
      ) : null}
    </main>
  );
}
