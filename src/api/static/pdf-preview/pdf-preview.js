import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/build/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/build/pdf.worker.min.mjs";

export class PdfPreview {
  constructor(rootElement) {
    this.rootElement = rootElement;
    this.container = document.createElement("div");
    this.container.className = "pdf-preview-container";
    this.rootElement.replaceChildren(this.container);

    this.pdfDoc = null;
    this.pageElements = new Map();
    this.highlights = [];
    this.scale = 1.35;
  }

  async loadPdf(fileUrl) {
    this.container.replaceChildren();
    this.pageElements.clear();
    this.highlights = [];

    const loadingTask = pdfjsLib.getDocument(fileUrl);
    this.pdfDoc = await loadingTask.promise;

    for (let pageNo = 1; pageNo <= this.pdfDoc.numPages; pageNo += 1) {
      const page = await this.pdfDoc.getPage(pageNo);
      const viewport = page.getViewport({ scale: this.scale });
      const wrapper = document.createElement("section");
      wrapper.className = "pdf-page";
      wrapper.dataset.pageNo = String(pageNo);

      const canvas = document.createElement("canvas");
      canvas.className = "pdf-canvas";
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;

      const highlightLayer = document.createElement("div");
      highlightLayer.className = "pdf-highlight-layer";

      wrapper.append(canvas, highlightLayer);
      this.container.append(wrapper);
      this.pageElements.set(pageNo, { wrapper, canvas, highlightLayer, viewport });

      const context = canvas.getContext("2d");
      await page.render({ canvasContext: context, viewport }).promise;
    }

    this.renderHighlights();
  }

  goToPage(pageNo) {
    const pageElement = this.pageElements.get(Number(pageNo));
    if (!pageElement) {
      return;
    }
    pageElement.wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  setHighlights(highlights) {
    this.highlights = Array.isArray(highlights) ? [...highlights] : [];
    this.renderHighlights();
  }

  addHighlight(highlight) {
    this.highlights.push(highlight);
    this.renderHighlights();
  }

  clearHighlights() {
    this.highlights = [];
    this.renderHighlights();
  }

  renderHighlights() {
    for (const pageElement of this.pageElements.values()) {
      pageElement.highlightLayer.replaceChildren();
    }

    for (const highlight of this.highlights) {
      const pageNo = Number(highlight.page_no);
      const pageElement = this.pageElements.get(pageNo);
      if (!pageElement) {
        continue;
      }

      const [x0, y0, x1, y1] = this.normalizeBbox(highlight.bbox_norm);
      const box = document.createElement("div");
      box.className = "pdf-highlight-box";
      box.style.left = `${x0 * 100}%`;
      box.style.top = `${y0 * 100}%`;
      box.style.width = `${(x1 - x0) * 100}%`;
      box.style.height = `${(y1 - y0) * 100}%`;

      pageElement.highlightLayer.append(box);
    }
  }

  normalizeBbox(bboxNorm) {
    if (!Array.isArray(bboxNorm) || bboxNorm.length !== 4) {
      throw new Error("bbox_norm must be an array: [x0, y0, x1, y1]");
    }

    const numbers = bboxNorm.map((value) => Number(value));
    if (numbers.some((value) => Number.isNaN(value))) {
      throw new Error("bbox_norm contains invalid numbers");
    }
    return numbers;
  }
}
