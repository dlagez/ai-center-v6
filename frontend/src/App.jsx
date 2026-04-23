import DoclingPdfPage from "./pages/docling-pdf";
import DoclingTaskMonitorPage from "./pages/docling-tasks";
import ExcelUpdateDetailPage from "./pages/excel-update/detail";
import ExcelUpdateTasksPage from "./pages/excel-update/tasks";
import FileManagerPage from "./pages/file-manager";
import HomePage from "./pages/home";
import KnowledgeBasePage from "./pages/knowledge-base";
import KnowledgeBaseDetailPage from "./pages/knowledge-base/detail";
import PdfPreviewDemoPage from "./pages/pdf-preview";
import TenderKbPage from "./pages/tender-kb";

export default function App() {
  const path = window.location.pathname;

  if (path === "/excel-update/tasks") {
    return <ExcelUpdateTasksPage />;
  }

  if (path === "/excel-update") {
    return <ExcelUpdateDetailPage />;
  }

  if (path === "/docling-pdf") {
    return <DoclingPdfPage />;
  }

  if (path === "/docling-tasks") {
    return <DoclingTaskMonitorPage />;
  }

  if (path === "/file-manager") {
    return <FileManagerPage />;
  }

  if (path === "/pdf-preview") {
    return <PdfPreviewDemoPage />;
  }

  if (path === "/tender-kb") {
    return <TenderKbPage />;
  }

  if (path === "/knowledge-base") {
    return <KnowledgeBasePage />;
  }

  if (path === "/knowledge-base/detail") {
    return <KnowledgeBaseDetailPage />;
  }

  return <HomePage />;
}
