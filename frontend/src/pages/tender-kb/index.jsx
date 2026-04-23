import { useEffect, useRef, useState } from "react";

import PdfPreview from "../../components/business/pdf-preview/PdfPreview";
import { askTenderKb, indexTenderKb } from "../../services/api/tenderKbApi";
import {
  getPdfPreviewFileUrl,
  listPdfPreviewFiles,
  uploadPdfFile,
} from "../../services/api/pdfPreviewApi";
import "./styles.css";

export default function TenderKbPage() {
  const previewRef = useRef(null);
  const [selectedUploadFile, setSelectedUploadFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [indexResult, setIndexResult] = useState(null);
  const [question, setQuestion] = useState("");
  const [qaResult, setQaResult] = useState(null);
  const [activeSourceId, setActiveSourceId] = useState("");
  const [status, setStatus] = useState("请选择或上传一个 PDF，然后开始解析并入库。");
  const [isIndexing, setIsIndexing] = useState(false);
  const [isAsking, setIsAsking] = useState(false);

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
    setIndexResult(null);
    setQaResult(null);
    setActiveSourceId("");
    setStatus(`已选择 ${file.file_name}`);
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!selectedUploadFile) {
      setStatus("请先选择 PDF 文件。");
      return;
    }

    try {
      setStatus("正在上传 PDF...");
      const uploaded = await uploadPdfFile(selectedUploadFile);
      await refreshFiles(uploaded.file_id);
      setStatus("上传成功，已加入文件列表。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "上传 PDF 失败");
    }
  };

  const handleIndex = async () => {
    if (!currentFile) {
      setStatus("请先选择一个 PDF 文件。");
      return;
    }
    try {
      setIsIndexing(true);
      setStatus(`正在解析并写入向量库：${currentFile.file_name}`);
      const payload = await indexTenderKb(currentFile.file_id);
      setIndexResult(payload);
      setQaResult(null);
      setActiveSourceId("");
      setStatus(`入库完成，共生成 ${payload.chunk_count} 个招投标专用 chunks。`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "解析入库失败");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleAsk = async (event) => {
    event.preventDefault();
    if (!currentFile) {
      setStatus("请先选择一个 PDF 文件。");
      return;
    }
    if (!question.trim()) {
      setStatus("请输入问题。");
      return;
    }
    try {
      setIsAsking(true);
      setStatus(`正在基于 ${currentFile.file_name} 进行知识库问答...`);
      const payload = await askTenderKb({
        fileId: currentFile.file_id,
        question,
      });
      setQaResult(payload);
      setActiveSourceId(payload.sources[0]?.id || "");
      setStatus("问答完成。");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "知识库问答失败");
    } finally {
      setIsAsking(false);
    }
  };

  const handleSelectSource = (source) => {
    setActiveSourceId(source.id);
    const pageNos = source.metadata?.page_nos || [];
    if (pageNos.length > 0) {
      previewRef.current?.goToPage(pageNos[0]);
    }
  };

  return (
    <main className="tender-kb-shell">
      <header className="tender-kb-topbar">
        <div>
          <p className="tender-kb-eyebrow">Tender KB</p>
          <h1>招投标 / 资格预审知识库</h1>
          <p className="tender-kb-lead">
            这个页面专门负责 PDF 解析、招投标专用 chunk、向量入库和知识库问答。
          </p>
        </div>
      </header>

      <section className="tender-kb-control-grid">
        <form className="tender-kb-card" onSubmit={handleUpload}>
          <div className="tender-kb-card-head">
            <strong>上传 PDF</strong>
            <span>先上传文件，再选择入库</span>
          </div>
          <input
            accept="application/pdf"
            onChange={(event) => setSelectedUploadFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button type="submit">上传 PDF</button>
        </form>

        <section className="tender-kb-card">
          <div className="tender-kb-card-head">
            <strong>知识库入库</strong>
            <span>使用 chunk_tender_document 进行专用切块</span>
          </div>
          <button disabled={!currentFile || isIndexing} onClick={handleIndex} type="button">
            {isIndexing ? "正在入库..." : "开始解析并入库"}
          </button>
          <div className="tender-kb-index-result">
            {indexResult ? (
              <pre>{JSON.stringify(indexResult, null, 2)}</pre>
            ) : (
              <span>尚未入库</span>
            )}
          </div>
        </section>
      </section>

      <section className="tender-kb-status-bar">{status}</section>

      <section className="tender-kb-file-card">
        <div className="tender-kb-file-head">
          <strong>PDF 文件列表</strong>
          <button className="button-secondary" onClick={() => refreshFiles(currentFile?.file_id ?? null)} type="button">
            刷新
          </button>
        </div>
        <div className="tender-kb-file-list">
          {files.map((file) => (
            <button
              className={`tender-kb-file-item ${currentFile?.file_id === file.file_id ? "is-active" : ""}`}
              key={file.file_id}
              onClick={() => selectFile(file)}
              type="button"
            >
              <strong>{file.file_name}</strong>
              <span>{file.folder_path}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="tender-kb-main">
        <section className="tender-kb-left">
          <section className="tender-kb-card">
            <div className="tender-kb-card-head">
              <strong>知识库问答</strong>
              <span>只针对当前选中文件检索</span>
            </div>
            <form className="tender-kb-qa-form" onSubmit={handleAsk}>
              <textarea
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="例如：资格预审文件要求申请人提供哪些资质证明材料？"
                rows="5"
                value={question}
              />
              <button disabled={!currentFile || isAsking} type="submit">
                {isAsking ? "正在提问..." : "开始问答"}
              </button>
            </form>
          </section>

          <section className="tender-kb-card">
            <div className="tender-kb-card-head">
              <strong>回答结果</strong>
            </div>
            <div className="tender-kb-answer">
              {qaResult ? <pre>{qaResult.answer}</pre> : <span>入库完成后可以在这里发起问答。</span>}
            </div>
          </section>

          <section className="tender-kb-card">
            <div className="tender-kb-card-head">
              <strong>命中片段</strong>
            </div>
            <div className="tender-kb-source-list">
              {qaResult?.sources?.length ? (
                qaResult.sources.map((source) => (
                  <button
                    className={`tender-kb-source-item ${activeSourceId === source.id ? "is-active" : ""}`}
                    key={source.id}
                    onClick={() => handleSelectSource(source)}
                    type="button"
                  >
                    <div className="tender-kb-source-line">
                      <strong>{source.metadata?.heading || "未命名片段"}</strong>
                      <span>{source.score.toFixed(3)}</span>
                    </div>
                    <div className="tender-kb-source-meta">
                      <span>类型：{source.metadata?.marker_type || "-"}</span>
                      <span>页码：{JSON.stringify(source.metadata?.page_nos || [])}</span>
                    </div>
                    <div className="tender-kb-source-text">{source.text}</div>
                  </button>
                ))
              ) : (
                <span>问答完成后显示命中片段。</span>
              )}
            </div>
          </section>
        </section>

        <section className="tender-kb-right">
          {fileUrl ? (
            <PdfPreview fileUrl={fileUrl} ref={previewRef} />
          ) : (
            <div className="tender-kb-empty">请选择 PDF 文件。</div>
          )}
        </section>
      </section>
    </main>
  );
}
