import DoclingPdfPage from "./pages/docling-pdf";
import DoclingTaskMonitorPage from "./pages/docling-tasks";
import ExcelUpdateDetailPage from "./pages/excel-update/detail";
import ExcelUpdateTasksPage from "./pages/excel-update/tasks";
import HomePage from "./pages/home";
import PdfPreviewDemoPage from "./pages/pdf-preview";

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

  if (path === "/pdf-preview") {
    return <PdfPreviewDemoPage />;
  }

  return <HomePage />;
}
