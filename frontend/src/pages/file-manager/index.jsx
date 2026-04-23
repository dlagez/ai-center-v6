import { useEffect, useMemo, useState } from "react";

import {
  deleteManagedFile,
  listManagedFiles,
  uploadManagedFile,
} from "../../services/api/fileManagerApi";
import "./styles.css";

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

export default function FileManagerPage() {
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState("正在加载文件列表...");
  const [isUploading, setIsUploading] = useState(false);
  const [bizType, setBizType] = useState("general");
  const [filterBizType, setFilterBizType] = useState("");
  const [keyword, setKeyword] = useState("");

  const bizTypeOptions = useMemo(() => {
    const values = new Set(files.map((item) => item.biz_type).filter(Boolean));
    return ["", ...Array.from(values)];
  }, [files]);

  const filteredFiles = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    if (!normalizedKeyword) {
      return files;
    }
    return files.filter((file) => {
      const targets = [
        file.file_name,
        file.object_name,
        file.folder_path,
        file.biz_type,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return targets.includes(normalizedKeyword);
    });
  }, [files, keyword]);

  const refreshFiles = async (nextBizType = filterBizType) => {
    const payload = await listManagedFiles({ bizType: nextBizType });
    setFiles(payload);
    setStatus("文件列表已加载。");
  };

  useEffect(() => {
    refreshFiles().catch((error) => {
      setStatus(error instanceof Error ? error.message : "加载文件列表失败");
    });
  }, []);

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    try {
      setIsUploading(true);
      setStatus(`正在上传 ${file.name}...`);
      const payload = await uploadManagedFile(file, { bizType });
      await refreshFiles();
      setStatus(`上传完成：${payload.file_name}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (fileId, fileName) => {
    const confirmed = window.confirm(`确认删除文件：${fileName}？`);
    if (!confirmed) {
      return;
    }
    try {
      setStatus(`正在删除 ${fileName}...`);
      await deleteManagedFile(fileId);
      await refreshFiles();
      setStatus(`已删除：${fileName}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "删除失败");
    }
  };

  const handleFilterChange = async (event) => {
    const value = event.target.value;
    setFilterBizType(value);
    try {
      setStatus("正在筛选文件...");
      await refreshFiles(value);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "筛选失败");
    }
  };

  return (
    <main className="file-manager-shell">
      <header className="file-manager-hero">
        <div>
          <p className="file-manager-eyebrow">File Manager</p>
          <h1>文件管理</h1>
          <p className="file-manager-lead">独立管理上传文件。这里只做上传、列表和删除，不做解析、切块或知识库入库。</p>
        </div>
        <a className="file-manager-back" href="/">
          返回主页
        </a>
      </header>

      <section className="file-manager-status">{status}</section>

      <section className="file-manager-toolbar">
        <div className="file-manager-upload-box">
          <label className="file-manager-field">
            <span>上传业务类型</span>
            <input onChange={(event) => setBizType(event.target.value)} value={bizType} />
          </label>
          <label className={`file-manager-upload-button ${isUploading ? "is-disabled" : ""}`}>
            <input disabled={isUploading} onChange={handleUpload} type="file" />
            {isUploading ? "上传中..." : "上传文件"}
          </label>
        </div>

        <div className="file-manager-filter-box">
          <label className="file-manager-field">
            <span>按业务类型筛选</span>
            <select onChange={handleFilterChange} value={filterBizType}>
              {bizTypeOptions.map((option) => (
                <option key={option || "all"} value={option}>
                  {option || "全部"}
                </option>
              ))}
            </select>
          </label>
          <label className="file-manager-field">
            <span>按文件名搜索</span>
            <input
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="输入文件名、目录或业务类型"
              value={keyword}
            />
          </label>
          <button className="file-manager-refresh" onClick={() => refreshFiles()} type="button">
            刷新
          </button>
        </div>
      </section>

      <section className="file-manager-table-shell">
        <div className="file-manager-table-head">
          <span>文件名</span>
          <span>业务类型</span>
          <span>目录</span>
          <span>类型</span>
          <span>大小</span>
          <span>上传时间</span>
          <span>操作</span>
        </div>

        <div className="file-manager-table-body">
          {filteredFiles.length ? (
            filteredFiles.map((file) => (
              <article className="file-manager-row" key={file.file_id}>
                <a className="file-manager-name file-manager-link" href={`/file-manager/detail?file_id=${file.file_id}`}>
                  <strong>{file.file_name}</strong>
                  <em>{file.object_name}</em>
                </a>
                <span>{file.biz_type}</span>
                <span>{file.folder_path}</span>
                <span>{file.content_type}</span>
                <span>{formatFileSize(file.file_size)}</span>
                <span>{formatTime(file.created_at)}</span>
                <button onClick={() => handleDelete(file.file_id, file.file_name)} type="button">
                  删除
                </button>
              </article>
            ))
          ) : (
            <div className="file-manager-empty">
              {files.length ? "没有匹配当前筛选条件的文件。" : "当前没有文件记录。"}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
