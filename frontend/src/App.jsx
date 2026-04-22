import ExcelUpdateDetailPage from "./pages/excel-update/detail";
import ExcelUpdateTasksPage from "./pages/excel-update/tasks";
import PdfPreviewDemoPage from "./pages/pdf-preview";

export default function App() {
  const path = window.location.pathname;

  if (path === "/excel-update/tasks") {
    return <ExcelUpdateTasksPage />;
  }

  if (path === "/excel-update") {
    return <ExcelUpdateDetailPage />;
  }

  return <PdfPreviewDemoPage />;
}
