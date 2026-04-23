import { useEffect, useMemo, useState } from "react";

import { getDoclingTaskDetail, listDoclingTasks } from "../../services/api/doclingTaskApi";
import "./styles.css";

const ACTIVE_STATUSES = new Set(["pending", "running"]);

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function statusTone(status) {
  switch (status) {
    case "success":
      return "is-success";
    case "failed":
      return "is-failed";
    case "partial_success":
      return "is-warning";
    case "running":
      return "is-running";
    default:
      return "is-pending";
  }
}

export default function DoclingTaskMonitorPage() {
  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [taskDetail, setTaskDetail] = useState(null);
  const [status, setStatus] = useState("正在加载解析任务...");
  const [loading, setLoading] = useState(true);

  const selectedTask = useMemo(
    () => tasks.find((task) => task.task_id === selectedTaskId) || null,
    [tasks, selectedTaskId],
  );

  const refreshTasks = async (nextSelectedTaskId = selectedTaskId) => {
    const payload = await listDoclingTasks();
    setTasks(payload);
    if (!payload.length) {
      setSelectedTaskId("");
      setTaskDetail(null);
      setStatus("当前还没有解析任务。");
      return;
    }

    const matched = payload.find((task) => task.task_id === nextSelectedTaskId) || payload[0];
    setSelectedTaskId(matched.task_id);
    setStatus(`已加载 ${payload.length} 条解析任务。`);
  };

  const refreshTaskDetail = async (taskId) => {
    if (!taskId) {
      return;
    }
    const payload = await getDoclingTaskDetail(taskId);
    setTaskDetail(payload);
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    refreshTasks()
      .catch((error) => {
        if (!cancelled) {
          setStatus(error instanceof Error ? error.message : "加载解析任务失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    refreshTaskDetail(selectedTaskId).catch((error) => {
      setStatus(error instanceof Error ? error.message : "加载任务详情失败");
    });
  }, [selectedTaskId]);

  useEffect(() => {
    const hasActiveTask = tasks.some((task) => ACTIVE_STATUSES.has(task.status));
    if (!hasActiveTask) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      refreshTasks(selectedTaskId)
        .then(() => refreshTaskDetail(selectedTaskId))
        .catch((error) => {
          setStatus(error instanceof Error ? error.message : "刷新解析任务失败");
        });
    }, 3000);

    return () => window.clearInterval(timer);
  }, [tasks, selectedTaskId]);

  return (
    <main className="docling-task-shell">
      <header className="docling-task-topbar">
        <div>
          <p className="docling-task-eyebrow">Parser Monitor</p>
          <h1>Docling 解析任务监控</h1>
          <p className="docling-task-lead">
            这个页面专门查看 PDF 解析任务进度，适合作为通用基础模块复用。
          </p>
        </div>
        <div className="docling-task-actions">
          <button onClick={() => refreshTasks().then(() => refreshTaskDetail(selectedTaskId))} type="button">
            刷新任务
          </button>
        </div>
      </header>

      <section className="docling-task-status-bar">
        <div>{status}</div>
      </section>

      <section className="docling-task-main">
        <section className="docling-task-list-panel">
          <div className="docling-task-panel-head">
            <h2>解析任务列表</h2>
            <span>{tasks.length} 条</span>
          </div>
          <div className="docling-task-list">
            {loading ? (
              <div className="docling-task-empty">正在加载任务...</div>
            ) : tasks.length ? (
              tasks.map((task) => (
                <button
                  className={`docling-task-card ${selectedTaskId === task.task_id ? "is-active" : ""}`}
                  key={task.task_id}
                  onClick={() => setSelectedTaskId(task.task_id)}
                  type="button"
                >
                  <div className="docling-task-card-line">
                    <strong>{task.file_name}</strong>
                    <span className={`docling-task-badge ${statusTone(task.status)}`}>{task.status}</span>
                  </div>
                  <div className="docling-task-card-meta">
                    <span>任务ID: {task.task_id}</span>
                    <span>版本: {task.parser_version}</span>
                    <span>创建时间: {formatTime(task.created_at)}</span>
                  </div>
                  <div className="docling-task-progress">
                    <div className="docling-task-progress-track">
                      <div className="docling-task-progress-fill" style={{ width: `${task.progress || 0}%` }} />
                    </div>
                    <span>{task.progress?.toFixed?.(2) ?? task.progress}%</span>
                  </div>
                  <div className="docling-task-card-grid">
                    <span>总页数 {task.total_pages}</span>
                    <span>已解析 {task.parsed_pages}</span>
                    <span>失败 {task.failed_pages}</span>
                    <span>当前批次 {task.current_batch_no}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="docling-task-empty">还没有解析任务。</div>
            )}
          </div>
        </section>

        <section className="docling-task-detail-panel">
          <div className="docling-task-panel-head">
            <h2>任务详情</h2>
            <span>{selectedTask?.file_name || "-"}</span>
          </div>

          {taskDetail ? (
            <div className="docling-task-detail-body">
              <section className="docling-task-summary-grid">
                <div>
                  <span>状态</span>
                  <strong>{taskDetail.status}</strong>
                </div>
                <div>
                  <span>进度</span>
                  <strong>{taskDetail.progress}%</strong>
                </div>
                <div>
                  <span>批大小</span>
                  <strong>{taskDetail.batch_size}</strong>
                </div>
                <div>
                  <span>当前批次</span>
                  <strong>{taskDetail.current_batch_no}</strong>
                </div>
                <div>
                  <span>总页数</span>
                  <strong>{taskDetail.total_pages}</strong>
                </div>
                <div>
                  <span>已解析页</span>
                  <strong>{taskDetail.parsed_pages}</strong>
                </div>
                <div>
                  <span>失败页</span>
                  <strong>{taskDetail.failed_pages}</strong>
                </div>
                <div>
                  <span>更新时间</span>
                  <strong>{formatTime(taskDetail.updated_at)}</strong>
                </div>
              </section>

              <section className="docling-task-subpanel">
                <div className="docling-task-subhead">
                  <h3>错误信息</h3>
                </div>
                <div className="docling-task-error-box">{taskDetail.error_message || "当前无任务级错误。"}</div>
              </section>

              <section className="docling-task-subpanel">
                <div className="docling-task-subhead">
                  <h3>失败页</h3>
                  <span>{taskDetail.failed_results.length} 条</span>
                </div>
                {taskDetail.failed_results.length ? (
                  <div className="docling-task-failed-list">
                    {taskDetail.failed_results.map((item) => (
                      <article className="docling-task-failed-item" key={`${item.batch_no}-${item.page_no}`}>
                        <strong>第 {item.page_no} 页</strong>
                        <span>批次 {item.batch_no}</span>
                        <span>{item.error_message || item.parse_status}</span>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="docling-task-empty-inline">当前没有失败页。</div>
                )}
              </section>

              <section className="docling-task-subpanel">
                <div className="docling-task-subhead">
                  <h3>页结果</h3>
                  <span>{taskDetail.page_results.length} 页</span>
                </div>
                <div className="docling-task-page-table">
                  <div className="docling-task-page-table-head">
                    <span>页码</span>
                    <span>批次</span>
                    <span>状态</span>
                    <span>块数</span>
                    <span>更新时间</span>
                  </div>
                  <div className="docling-task-page-table-body">
                    {taskDetail.page_results.map((item) => (
                      <div className="docling-task-page-row" key={`${item.batch_no}-${item.page_no}`}>
                        <span>{item.page_no}</span>
                        <span>{item.batch_no}</span>
                        <span className={`docling-task-badge ${statusTone(item.parse_status)}`}>{item.parse_status}</span>
                        <span>{item.block_count}</span>
                        <span>{formatTime(item.updated_at)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          ) : (
            <div className="docling-task-empty">请选择一个任务查看详情。</div>
          )}
        </section>
      </section>
    </main>
  );
}
