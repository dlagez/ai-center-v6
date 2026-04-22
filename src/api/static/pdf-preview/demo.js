import { PdfPreview } from "/static/pdf-preview/pdf-preview.js";

const uploadForm = document.querySelector("#upload-form");
const fileInput = document.querySelector("#pdf-file");
const goToPageInput = document.querySelector("#go-to-page");
const goToPageButton = document.querySelector("#go-to-page-btn");
const highlightPageInput = document.querySelector("#highlight-page");
const highlightBboxInput = document.querySelector("#highlight-bbox");
const addHighlightButton = document.querySelector("#add-highlight-btn");
const clearHighlightButton = document.querySelector("#clear-highlight-btn");
const sessionOutput = document.querySelector("#session-output");
const previewRoot = document.querySelector("#pdf-preview-root");

const preview = new PdfPreview(previewRoot);
let currentSession = null;

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const [file] = fileInput.files || [];
  if (!file) {
    alert("请选择 PDF 文件");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/pdf-preview/sessions", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    alert(payload.detail || "上传失败");
    return;
  }

  currentSession = payload;
  sessionOutput.textContent = JSON.stringify(payload, null, 2);
  await preview.loadPdf(payload.file_url);
});

goToPageButton.addEventListener("click", () => {
  preview.goToPage(Number(goToPageInput.value || 1));
});

addHighlightButton.addEventListener("click", () => {
  if (!currentSession) {
    alert("请先上传并加载 PDF");
    return;
  }

  try {
    const highlight = {
      page_no: Number(highlightPageInput.value || 1),
      bbox_norm: JSON.parse(highlightBboxInput.value),
    };
    preview.addHighlight(highlight);
    preview.goToPage(highlight.page_no);
  } catch (error) {
    alert(error instanceof Error ? error.message : "高亮参数格式错误");
  }
});

clearHighlightButton.addEventListener("click", () => {
  preview.clearHighlights();
});
