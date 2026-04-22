import { useEffect, useRef, useState } from "react";

import PdfPreview from "../../components/business/pdf-preview/PdfPreview";
import {
  getPdfPreviewFileUrl,
  listPdfPreviewFiles,
  uploadPdfFile,
} from "../../services/api/pdfPreviewApi";
import "./styles.css";

function parseBBox(value) {
  const parsed = JSON.parse(value);
  if (!Array.isArray(parsed) || parsed.length !== 4) {
    throw new Error("bbox_norm must be [x0, y0, x1, y1]");
  }
  return parsed;
}

export default function PdfPreviewDemoPage() {
  const previewRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [pageNo, setPageNo] = useState(1);
  const [bboxText, setBboxText] = useState("[0.1,0.1,0.6,0.2]");
  const [highlights, setHighlights] = useState([]);
  const [status, setStatus] = useState("请选择一个 PDF 文件进行预览。");

  const refreshFiles = async (nextCurrentFileId = null) => {
    const nextFiles = await listPdfPreviewFiles();
    setFiles(nextFiles);
    if (nextCurrentFileId) {
      const matched = nextFiles.find((item) => item.file_id === nextCurrentFileId) || null;
      setCurrentFile(matched);
      return matched;
    }
    return nextFiles;
  };

  const selectFile = (file) => {
    setCurrentFile(file);
    const nextFileUrl = getPdfPreviewFileUrl(file.file_id);
    setFileUrl(nextFileUrl);
    setHighlights([]);
    previewRef.current?.clearHighlights();
    setStatus(`已加载 ${file.file_name}`);
  };

  const loadPdf = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setStatus("请先选择 PDF 文件。");
      return;
    }

    try {
      setStatus("正在上传 PDF...");
      const uploaded = await uploadPdfFile(selectedFile);
      const nextCurrentFile = await refreshFiles(uploaded.file_id);
      if (nextCurrentFile) {
        selectFile(nextCurrentFile);
      }
      setStatus("PDF 已加载，可以继续调试高亮。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "上传 PDF 失败");
    }
  };

  const goToPage = () => {
    previewRef.current?.goToPage(pageNo);
  };

  const addHighlight = () => {
    try {
      const highlight = {
        page_no: Number(pageNo),
        bbox_norm: parseBBox(bboxText),
      };
      setHighlights((current) => [...current, highlight]);
      previewRef.current?.addHighlight(highlight);
      previewRef.current?.goToPage(highlight.page_no);
      setStatus(`已添加第 ${highlight.page_no} 页高亮。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "高亮参数错误");
    }
  };

  const clearHighlights = () => {
    setHighlights([]);
    previewRef.current?.clearHighlights();
    setStatus("高亮已清空。");
  };

  useEffect(() => {
    const loadInitialFiles = async () => {
      try {
        const nextFiles = await refreshFiles();
        if (Array.isArray(nextFiles) && nextFiles.length > 0) {
          selectFile(nextFiles[0]);
        }
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "加载 PDF 列表失败");
      }
    };

    loadInitialFiles();
  }, []);

  return (
    <main className="demo-shell">
      <section className="demo-sidebar">
        <p className="demo-eyebrow">React Demo</p>
        <h1>PDF Preview</h1>
        <p className="demo-lead">
          上传文件会写入数据库和 MinIO。左侧展示数据库里已有 PDF，点击即可预览，并通过
          <code> pdf.js </code>叠加 `bbox_norm` 高亮框。
        </p>

        <form className="demo-card" onSubmit={loadPdf}>
          <label className="demo-field">
            <span>选择 PDF</span>
            <input
              accept="application/pdf"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
          <button type="submit">上传并加载</button>
        </form>

        <section className="demo-card">
          <div className="demo-section-head">
            <h2>PDF 文件列表</h2>
            <button
              className="button-secondary"
              onClick={() => refreshFiles(currentFile?.file_id ?? null)}
              type="button"
            >
              刷新列表
            </button>
          </div>
          <div className="file-list">
            {files.length ? (
              files.map((file) => (
                <button
                  className={`file-list-item ${currentFile?.file_id === file.file_id ? "is-active" : ""}`}
                  key={file.file_id}
                  onClick={() => selectFile(file)}
                  type="button"
                >
                  <strong>{file.file_name}</strong>
                  <span>{file.folder_path}</span>
                </button>
              ))
            ) : (
              <div className="file-list-empty">当前还没有 PDF 记录。</div>
            )}
          </div>
        </section>

        <section className="demo-card">
          <label className="demo-field">
            <span>页码</span>
            <input
              min="1"
              onChange={(event) => setPageNo(Number(event.target.value || 1))}
              step="1"
              type="number"
              value={pageNo}
            />
          </label>
          <div className="demo-actions">
            <button onClick={goToPage} type="button">
              跳转页码
            </button>
          </div>
        </section>

        <section className="demo-card">
          <label className="demo-field">
            <span>bbox_norm</span>
            <input onChange={(event) => setBboxText(event.target.value)} type="text" value={bboxText} />
          </label>
          <div className="demo-actions">
            <button onClick={addHighlight} type="button">
              添加高亮
            </button>
            <button className="button-secondary" onClick={clearHighlights} type="button">
              清空高亮
            </button>
          </div>
        </section>

        <section className="demo-card">
          <h2>状态</h2>
          <pre>{status}</pre>
        </section>

        <section className="demo-card">
          <h2>当前文件</h2>
          <pre>{currentFile ? JSON.stringify(currentFile, null, 2) : "尚未选择 PDF"}</pre>
        </section>
      </section>

      <section className="demo-preview">
        {fileUrl ? (
          <PdfPreview fileUrl={fileUrl} highlights={highlights} ref={previewRef} />
        ) : (
          <div className="demo-empty">上传 PDF 后将在这里显示连续分页预览。</div>
        )}
      </section>
    </main>
  );
}
