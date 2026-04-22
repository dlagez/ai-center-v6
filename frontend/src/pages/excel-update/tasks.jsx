import { useEffect, useState } from "react";

import {
  createExcelUpdateTask,
  listExcelUpdateTasks,
} from "../../services/api/excelUpdateApi";
import "./excel-update.css";

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function toText(value) {
  return value == null || value === "" ? "未设置" : String(value);
}

export default function ExcelUpdateTasksPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [status, setStatus] = useState("正在加载任务列表...");
  const [isError, setIsError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadTasks = async () => {
    const payload = await listExcelUpdateTasks();
    setTasks(payload);
    return payload;
  };

  useEffect(() => {
    loadTasks()
      .then(() => {
        setStatus("任务列表已加载");
        setIsError(false);
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "加载任务列表失败");
        setIsError(true);
      });
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setStatus("请先选择 Excel 文件。");
      setIsError(true);
      return;
    }

    try {
      setSubmitting(true);
      setStatus("正在创建任务...");
      setIsError(false);
      const payload = await createExcelUpdateTask(selectedFile);
      window.location.href = `/excel-update?task_id=${encodeURIComponent(payload.task_id)}`;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "创建任务失败");
      setIsError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="excel-page">
      <section className="excel-hero">
        <h1>Excel 任务列表</h1>
        <p>这里统一管理任务。先新建任务，再进入详情页持续追加字段更新。</p>
      </section>

      <section className="excel-layout">
        <article className="excel-panel">
          <div className="excel-panel-head">
            <h2>新建任务</h2>
            <p>上传一个 Excel，系统会创建一个持久任务。</p>
          </div>
          <div className="excel-panel-body">
            <form className="excel-form" onSubmit={handleSubmit}>
              <label className="excel-field">
                <span>上传 Excel</span>
                <input
                  accept=".xlsx"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  type="file"
                />
              </label>
              <div className="excel-actions">
                <button disabled={submitting} type="submit">
                  创建任务
                </button>
                <button
                  className="button-secondary"
                  onClick={() =>
                    loadTasks()
                      .then(() => {
                        setStatus("任务列表已刷新");
                        setIsError(false);
                      })
                      .catch((error) => {
                        setStatus(error instanceof Error ? error.message : "刷新任务列表失败");
                        setIsError(true);
                      })
                  }
                  type="button"
                >
                  刷新列表
                </button>
              </div>
              <div className={`excel-status ${isError ? "is-error" : ""}`}>{status}</div>
            </form>
          </div>
        </article>

        <article className="excel-panel">
          <div className="excel-panel-head">
            <h2>任务表格</h2>
            <p>点击任意一行即可打开当前任务详情页。</p>
          </div>
          <div className="excel-panel-body">
            {tasks.length ? (
              <div className="excel-table-shell">
                <table className="excel-table">
                  <thead>
                    <tr>
                      <th>文件名</th>
                      <th>任务 ID</th>
                      <th>操作次数</th>
                      <th>最新列</th>
                      <th>更新时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task) => (
                      <tr
                        key={task.task_id}
                        onClick={() => {
                          window.location.href = `/excel-update?task_id=${encodeURIComponent(task.task_id)}`;
                        }}
                      >
                        <td>
                          <div className="excel-file-name">{task.file_name}</div>
                        </td>
                        <td>
                          <div className="excel-task-id">{task.task_id}</div>
                        </td>
                        <td>{task.operation_count}</td>
                        <td>{toText(task.latest_target_column)}</td>
                        <td>{formatDate(task.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="excel-empty">还没有任务，先创建一个。</div>
            )}
          </div>
        </article>
      </section>
    </main>
  );
}
