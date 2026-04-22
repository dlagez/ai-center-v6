import { useEffect, useMemo, useRef, useState } from "react";

import PdfPreview from "../../components/business/pdf-preview/PdfPreview";
import { parseDoclingPdf } from "../../services/api/doclingPdfApi";
import {
  getPdfPreviewFileUrl,
  listPdfPreviewFiles,
  uploadPdfFile,
} from "../../services/api/pdfPreviewApi";
import "./styles.css";

export default function DoclingPdfPage() {
  const previewRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [parseState, setParseState] = useState("未开始");
  const [parseResult, setParseResult] = useState(null);
  const [activeBlock, setActiveBlock] = useState(null);
  const [status, setStatus] = useState("请选择一个 PDF 文件，然后开始解析。");

  const groupedBlocks = useMemo(() => {
    const groups = new Map();
    for (const block of parseResult?.blocks || []) {
      const pageNo = block.page_no || 0;
      if (!groups.has(pageNo)) {
        groups.set(pageNo, []);
      }
      groups.get(pageNo).push(block);
    }
    return [...groups.entries()].sort((a, b) => a[0] - b[0]);
  }, [parseResult]);

  const refreshFiles = async (nextFileId = null) => {
    const nextFiles = await listPdfPreviewFiles();
    setFiles(nextFiles);
    if (nextFileId) {
      const matched = nextFiles.find((item) => item.file_id === nextFileId) || null;
      if (matched) {
        selectFile(matched);
      }
      return matched;
    }
    return nextFiles;
  };

  useEffect(() => {
    refreshFiles().catch((error) => {
      setStatus(error instanceof Error ? error.message : "加载 PDF 文件列表失败");
    });
  }, []);

  const selectFile = (file) => {
    setCurrentFile(file);
    setFileUrl(getPdfPreviewFileUrl(file.file_id));
    setParseResult(null);
    setActiveBlock(null);
    setParseState("未开始");
    setStatus(`已选择 ${file.file_name}`);
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setStatus("请先选择 PDF 文件。");
      return;
    }

    try {
      setStatus("正在上传 PDF...");
      const uploaded = await uploadPdfFile(selectedFile);
      await refreshFiles(uploaded.file_id);
      setStatus("上传成功，已加入文件列表。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "上传 PDF 失败");
    }
  };

  const handleParse = async (targetFile = currentFile) => {
    if (!targetFile) {
      setStatus("请先选择一个 PDF 文件。");
      return;
    }

    try {
      setParseState("解析中");
      setCurrentFile(targetFile);
      setFileUrl(getPdfPreviewFileUrl(targetFile.file_id));
      setStatus(`正在使用 Docling 解析 ${targetFile.file_name} ...`);
      const payload = await parseDoclingPdf(targetFile.file_id);
      setParseResult(payload);
      setParseState(payload.status === "success" ? "成功" : "失败");
      if (payload.status !== "success") {
        setStatus(payload.error || "解析失败");
        return;
      }

      const firstBlock =
        payload.blocks.find((block) => block.page_no && block.bbox_norm) || payload.blocks[0] || null;
      setActiveBlock(firstBlock);
      setStatus(`解析成功：${targetFile.file_name}`);
    } catch (error) {
      setParseState("失败");
      setStatus(error instanceof Error ? error.message : "解析失败");
    }
  };

  const handleSelectBlock = (block) => {
    setActiveBlock(block);
    if (block.page_no) {
      previewRef.current?.goToPage(block.page_no);
    }
    if (block.page_no && block.bbox_norm) {
      previewRef.current?.setHighlights([
        {
          page_no: block.page_no,
          bbox_norm: block.bbox_norm,
        },
      ]);
    } else {
      previewRef.current?.clearHighlights();
    }
  };

  return (
    <main className="docling-shell">
      <header className="docling-topbar">
        <div>
          <p className="docling-eyebrow">Docling Visualizer</p>
          <h1>Docling PDF 解析可视化</h1>
          <p className="docling-lead">
            上方选择文件并开始解析，下方左侧查看解析块，右侧原 PDF 自动定位并用红框高亮当前块。
          </p>
        </div>
        <div className="docling-status"><strong>状态</strong><span>{parseState}</span></div>
      </header>

      <section className="docling-control-grid">
        <form className="docling-upload-card" onSubmit={handleUpload}>
          <div className="docling-card-head">
            <strong>上传 PDF</strong>
            <span>先上传文件，再从列表中选择</span>
          </div>
          <input
            accept="application/pdf"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button type="submit">上传 PDF</button>
        </form>
      </section>

      <section className="docling-status-bar">
        <div className="docling-message">{status}</div>
      </section>

      <section className="docling-file-card">
        <div className="docling-file-head">
          <strong>PDF 文件列表</strong>
          <button className="button-secondary" onClick={() => refreshFiles(currentFile?.file_id ?? null)} type="button">
            刷新
          </button>
        </div>
        <div className="docling-file-list">
          {files.map((file) => (
            <div
              className={`docling-file-item ${currentFile?.file_id === file.file_id ? "is-active" : ""}`}
              key={file.file_id}
            >
              <button className="docling-file-select" onClick={() => selectFile(file)} type="button">
                <strong>{file.file_name}</strong>
                <span>{file.folder_path}</span>
              </button>
              <button
                className="docling-file-parse"
                onClick={() => {
                  selectFile(file);
                  handleParse(file);
                }}
                type="button"
              >
                开始解析
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="docling-main">
        <section className="docling-left">
          {parseResult?.status === "failed" ? (
            <article className="docling-panel docling-error-panel">
              <div className="docling-panel-head">
                <h2>错误信息</h2>
              </div>
              <pre>{parseResult.error || "解析失败"}</pre>
            </article>
          ) : groupedBlocks.length ? (
            <article className="docling-panel">
              <div className="docling-panel-head">
                <h2>解析块列表</h2>
                <span>{parseResult?.file_name}</span>
              </div>
              <div className="docling-block-groups">
                {groupedBlocks.map(([pageNo, blocks]) => (
                  <div className="docling-block-group" key={pageNo}>
                    <h3>第 {pageNo} 页</h3>
                    {blocks.map((block, index) => (
                      <button
                        className={`docling-block-item ${activeBlock?.raw_path === block.raw_path ? "is-active" : ""}`}
                        key={`${block.raw_path}-${index}`}
                        onClick={() => handleSelectBlock(block)}
                        type="button"
                      >
                        <div className="docling-block-line">
                          <strong>{block.label || "unknown"}</strong>
                          <span>{block.page_no ?? "-"}</span>
                        </div>
                        <div className="docling-block-text">{block.text_preview || ""}</div>
                        <div className="docling-block-meta">
                          <span>bbox: {Array.isArray(block.bbox) ? JSON.stringify(block.bbox) : ""}</span>
                          <span>coord_origin: {block.coord_origin || ""}</span>
                          <span>self_ref: {block.self_ref || ""}</span>
                          <span>parent: {block.parent || ""}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </article>
          ) : (
            <div className="docling-empty">开始解析后，这里显示 Docling 识别出的块列表。</div>
          )}
        </section>

        <section className="docling-right">
          {fileUrl ? (
            <PdfPreview
              fileUrl={fileUrl}
              highlights={
                activeBlock?.page_no && activeBlock?.bbox_norm
                  ? [{ page_no: activeBlock.page_no, bbox_norm: activeBlock.bbox_norm }]
                  : []
              }
              ref={previewRef}
            />
          ) : (
            <div className="docling-empty">请选择 PDF 文件。</div>
          )}
        </section>
      </section>
    </main>
  );
}
