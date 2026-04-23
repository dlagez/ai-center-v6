import ExcelUpdateDetailPage from "./pages/excel-update/detail";
import ExcelUpdateTasksPage from "./pages/excel-update/tasks";
import FileManagerPage from "./pages/file-manager";
import FileManagerDetailPage from "./pages/file-manager/detail";
import HomePage from "./pages/home";
import KnowledgeBasePage from "./pages/knowledge-base";
import KnowledgeBaseDetailPage from "./pages/knowledge-base/detail";
import PdfPreviewDemoPage from "./pages/pdf-preview";

export default function App() {
  const path = window.location.pathname;

  if (path === "/excel-update/tasks") {
    return <ExcelUpdateTasksPage />;
  }

  if (path === "/excel-update") {
    return <ExcelUpdateDetailPage />;
  }

  if (path === "/file-manager") {
    return <FileManagerPage />;
  }

  if (path === "/file-manager/detail") {
    return <FileManagerDetailPage />;
  }

  if (path === "/pdf-preview") {
    return <PdfPreviewDemoPage />;
  }

  if (path === "/knowledge-base") {
    return <KnowledgeBasePage />;
  }

  if (path === "/knowledge-base/detail") {
    return <KnowledgeBaseDetailPage />;
  }

  return <HomePage />;
}
