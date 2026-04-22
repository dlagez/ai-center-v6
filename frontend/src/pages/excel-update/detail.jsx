import { useEffect, useMemo, useState } from "react";

import {
  createExcelUpdateOperation,
  getExcelUpdateTask,
} from "../../services/api/excelUpdateApi";
import "./excel-update.css";

const promptShortcuts = [
  "使用源excel的项目编号、回款金额，来更新清欠表的3月回款。",
  "调用 PM API 获取 3 月实际产值数据，更新这张表的 3 月实际产值。",
];

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function toText(value) {
  return value == null || value === "" ? "未设置" : String(value);
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

export default function ExcelUpdateDetailPage() {
  const taskId = useMemo(
    () => new URLSearchParams(window.location.search).get("task_id") || "",
    [],
  );
  const [task, setTask] = useState(null);
  const [status, setStatus] = useState("");
  const [isError, setIsError] = useState(false);
  const [sourceType, setSourceType] = useState("pm_api");
  const [sourceFile, setSourceFile] = useState(null);
  const [userPrompt, setUserPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  const loadDetail = async () => {
    if (!taskId) {
      throw new Error("缺少 task_id，请从任务列表页进入。");
    }
    const payload = await getExcelUpdateTask(taskId);
    setTask(payload);
    return payload;
  };

  useEffect(() => {
    loadDetail()
      .then(() => {
        setStatus(`任务详情已加载：${taskId}`);
        setIsError(false);
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "初始化页面失败");
        setIsError(true);
      });
  }, [taskId]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!taskId) {
      setStatus("缺少任务 ID，请从任务列表页进入。");
      setIsError(true);
      return;
    }

    if (sourceType === "excel_file" && !sourceFile) {
      setStatus("请选择源 Excel 文件");
      setIsError(true);
      return;
    }

    try {
      setBusy(true);
      setStatus("正在执行更新操作...");
      setIsError(false);
      const payload = await createExcelUpdateOperation(taskId, {
        sourceType,
        sourceFile,
        userPrompt: userPrompt.trim(),
      });
      await loadDetail();
      setStatus(`已完成第 ${payload.sequence} 次操作，更新列：${payload.request?.target_column || "未指定"}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "执行更新操作失败");
      setIsError(true);
    } finally {
      setBusy(false);
    }
  };

  const orderedOperations = useMemo(() => {
    if (!task?.operations) return [];
    return [...task.operations].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }, [task]);

  return (
    <main className="excel-page">
      <section className="excel-hero">
        <h1>Excel 任务详情</h1>
        <p>在同一个任务下连续执行多次字段更新。默认只显示摘要，详细日志按需展开。</p>
      </section>

      <div className="excel-topbar">
        <a className="button-link" href="/excel-update/tasks">
          返回任务列表
        </a>
        <button
          className="button-secondary"
          onClick={() =>
            loadDetail()
              .then(() => {
                setStatus(`任务详情已刷新：${taskId}`);
                setIsError(false);
              })
              .catch((error) => {
                setStatus(error instanceof Error ? error.message : "刷新任务详情失败");
                setIsError(true);
              })
          }
          type="button"
        >
          刷新当前详情
        </button>
      </div>

      <section className="excel-panel">
        <div className="excel-panel-head">
          <h2>执行操作</h2>
          <p>输入本次更新说明后再执行。完成后会在下方追加新的日志记录。</p>
        </div>
        <div className="excel-panel-body">
          <form className="excel-form" onSubmit={handleSubmit}>
            <div className="excel-compact-row">
              <label className="excel-field">
                <span>当前任务 ID</span>
                <input readOnly type="text" value={taskId} />
              </label>
              <label className="excel-field">
                <span>数据来源</span>
                <select onChange={(event) => setSourceType(event.target.value)} value={sourceType}>
                  <option value="pm_api">PM/API</option>
                  <option value="excel_file">源 Excel</option>
                </select>
              </label>
            </div>

            {sourceType === "excel_file" ? (
              <label className="excel-field">
                <span>源 Excel 文件</span>
                <input accept=".xlsx" onChange={(event) => setSourceFile(event.target.files?.[0] ?? null)} type="file" />
              </label>
            ) : null}

            <label className="excel-field">
              <span>操作说明</span>
              <textarea onChange={(event) => setUserPrompt(event.target.value)} value={userPrompt} />
            </label>

            <div className="excel-chip-row">
              {promptShortcuts.map((prompt) => (
                <button
                  className="excel-chip"
                  key={prompt}
                  onClick={() => setUserPrompt(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="excel-actions">
              <button disabled={busy} type="submit">
                执行当前操作
              </button>
            </div>
            <div className={`excel-status ${isError ? "is-error" : ""}`}>{status}</div>
          </form>
        </div>
      </section>

      <section className="excel-panel">
        <div className="excel-panel-head">
          <h2>操作日志</h2>
          <p>默认只展示摘要信息。需要时再点击展开操作记录和变更记录。</p>
        </div>
        <div className="excel-panel-body">
          {orderedOperations.length ? (
            <div className="excel-log-list">
              {orderedOperations.map((op) => (
                <article className="excel-log-item" key={op.operation_id}>
                  <div className="excel-log-head">
                    <div>
                      <strong>第 {op.sequence} 次操作</strong>
                      <div className="excel-muted">{formatDate(op.created_at)}</div>
                    </div>
                    <a className="button-link" href={op.download_url} rel="noreferrer" target="_blank">
                      下载本次表格
                    </a>
                  </div>
                  <div className="excel-pill-row">
                    <span className="excel-pill">来源：{op.request?.source_type === "excel_file" ? "源 Excel" : "PM/API"}</span>
                    <span className="excel-pill">Sheet：{toText(op.analysis?.sheet_name || op.request?.sheet_name)}</span>
                    <span className="excel-pill">目标列：{toText(op.request?.target_column)}</span>
                    <span className="excel-pill">更新单元格：{op.result?.summary?.updated_cells ?? 0}</span>
                  </div>
                  <details className="excel-details">
                    <summary>操作记录</summary>
                    <pre>{pretty(op.request)}</pre>
                  </details>
                  <details className="excel-details">
                    <summary>变更记录</summary>
                    <pre>{pretty(op.result?.changes || [])}</pre>
                  </details>
                </article>
              ))}
            </div>
          ) : (
            <div className="excel-empty">这个任务还没有任何操作记录。</div>
          )}
        </div>
      </section>

      <section className="excel-panel">
        <div className="excel-panel-head">
          <h2>任务摘要</h2>
          <p>这里展示任务级别状态和当前最新输出文件。</p>
        </div>
        <div className="excel-panel-body">
          {task ? (
            <div className="excel-meta-grid">
              <div className="excel-meta-item"><div className="excel-label">文件名</div><div>{task.file_name}</div></div>
              <div className="excel-meta-item"><div className="excel-label">任务 ID</div><div>{task.task_id}</div></div>
              <div className="excel-meta-item"><div className="excel-label">创建时间</div><div>{formatDate(task.created_at)}</div></div>
              <div className="excel-meta-item"><div className="excel-label">更新时间</div><div>{formatDate(task.updated_at)}</div></div>
              <div className="excel-meta-item"><div className="excel-label">操作次数</div><div>{task.operation_count}</div></div>
              <div className="excel-meta-item"><div className="excel-label">当前最新列</div><div>{toText(task.latest_target_column)}</div></div>
              <div className="excel-meta-item"><div className="excel-label">当前文件</div><div>{task.latest_output_file_name}</div></div>
              <div className="excel-meta-item">
                <div className="excel-label">下载当前最新文件</div>
                <div><a className="button-link" href={task.download_url} rel="noreferrer" target="_blank">下载最新表格</a></div>
              </div>
            </div>
          ) : (
            <div className="excel-empty">正在加载任务摘要...</div>
          )}
        </div>
      </section>
    </main>
  );
}
