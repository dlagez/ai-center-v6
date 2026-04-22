import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import * as pdfjsLib from "pdfjs-dist/build/pdf.mjs";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import "./pdf-preview.css";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

function normalizeBbox(bboxNorm) {
  if (!Array.isArray(bboxNorm) || bboxNorm.length !== 4) {
    throw new Error("bbox_norm must be an array: [x0, y0, x1, y1]");
  }

  const numbers = bboxNorm.map((value) => Number(value));
  if (numbers.some((value) => Number.isNaN(value))) {
    throw new Error("bbox_norm contains invalid numbers");
  }

  return numbers;
}

const PdfPreview = forwardRef(function PdfPreview(
  { fileUrl = "", highlights = [], scale = 1.35 },
  ref,
) {
  const rootRef = useRef(null);
  const pageElementsRef = useRef(new Map());
  const [currentFileUrl, setCurrentFileUrl] = useState(fileUrl);
  const [currentHighlights, setCurrentHighlights] = useState(highlights);
  const renderVersionRef = useRef(0);

  const renderHighlights = () => {
    for (const pageElement of pageElementsRef.current.values()) {
      pageElement.highlightLayer.replaceChildren();
    }

    for (const highlight of currentHighlights) {
      const pageNo = Number(highlight.page_no);
      const pageElement = pageElementsRef.current.get(pageNo);
      if (!pageElement) {
        continue;
      }

      const [x0, y0, x1, y1] = normalizeBbox(highlight.bbox_norm);
      const box = document.createElement("div");
      box.className = "pdf-highlight-box";
      box.style.left = `${x0 * 100}%`;
      box.style.top = `${y0 * 100}%`;
      box.style.width = `${(x1 - x0) * 100}%`;
      box.style.height = `${(y1 - y0) * 100}%`;
      pageElement.highlightLayer.append(box);
    }
  };

  const goToPage = (pageNo) => {
    const pageElement = pageElementsRef.current.get(Number(pageNo));
    if (!pageElement) {
      return;
    }

    pageElement.wrapper.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const renderPdfDocument = async (nextFileUrl) => {
    if (!rootRef.current) {
      return;
    }

    const renderVersion = renderVersionRef.current + 1;
    renderVersionRef.current = renderVersion;
    rootRef.current.replaceChildren();
    pageElementsRef.current.clear();

    if (!nextFileUrl) {
      return;
    }

    const loadingTask = pdfjsLib.getDocument(nextFileUrl);
    const pdfDoc = await loadingTask.promise;
    if (renderVersion !== renderVersionRef.current || !rootRef.current) {
      return;
    }

    for (let pageNo = 1; pageNo <= pdfDoc.numPages; pageNo += 1) {
      const page = await pdfDoc.getPage(pageNo);
      if (renderVersion !== renderVersionRef.current || !rootRef.current) {
        return;
      }
      const viewport = page.getViewport({ scale });
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
      rootRef.current.append(wrapper);
      pageElementsRef.current.set(pageNo, { wrapper, highlightLayer });

      const context = canvas.getContext("2d");
      await page.render({ canvasContext: context, viewport }).promise;
      if (renderVersion !== renderVersionRef.current) {
        return;
      }
    }
  };

  useImperativeHandle(
    ref,
    () => ({
      loadPdf: (nextFileUrl) => {
        setCurrentFileUrl(nextFileUrl);
      },
      goToPage,
      setHighlights: (nextHighlights) => {
        setCurrentHighlights(Array.isArray(nextHighlights) ? [...nextHighlights] : []);
      },
      addHighlight: (highlight) => {
        setCurrentHighlights((previous) => [...previous, highlight]);
      },
      clearHighlights: () => {
        setCurrentHighlights([]);
      },
    }),
    [],
  );

  useEffect(() => {
    setCurrentFileUrl(fileUrl);
  }, [fileUrl]);

  useEffect(() => {
    setCurrentHighlights(highlights);
  }, [highlights]);

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        await renderPdfDocument(currentFileUrl);
        if (active) {
          renderHighlights();
        }
      } catch (error) {
        console.error("Failed to render PDF", error);
      }
    };

    run();

    return () => {
      active = false;
      renderVersionRef.current += 1;
    };
  }, [currentFileUrl, scale]);

  useEffect(() => {
    renderHighlights();
  }, [currentHighlights]);

  return <div className="pdf-preview-container" ref={rootRef} />;
});

export default PdfPreview;
