import "./styles.css";

const NAV_ITEMS = [
  {
    title: "PDF 预览",
    path: "/pdf-preview",
    description: "上传 PDF、查看文件列表，并使用原始 PDF 预览与高亮框调试。",
  },
  {
    title: "Docling PDF 可视化",
    path: "/docling-pdf",
    description: "选择 PDF 后触发 Docling 解析，联动查看块列表与 PDF 定位高亮。",
  },
  {
    title: "Docling 任务监控",
    path: "/docling-tasks",
    description: "查看解析任务状态、进度、失败页和每页结果，作为基础监控模块复用。",
  },
  {
    title: "Excel 任务列表",
    path: "/excel-update/tasks",
    description: "查看 Excel 更新任务列表，进入具体任务详情页继续处理。",
  },
];

export default function HomePage() {
  return (
    <main className="home-shell">
      <section className="home-hero">
        <p className="home-eyebrow">AI Center V6</p>
        <h1>前端功能导航</h1>
        <p className="home-lead">
          这里汇总当前可用的调试页和业务页，后续新增模块也可以继续挂到这个主页里。
        </p>
      </section>

      <section className="home-grid">
        {NAV_ITEMS.map((item) => (
          <a className="home-card" href={item.path} key={item.path}>
            <div className="home-card-head">
              <h2>{item.title}</h2>
              <span>{item.path}</span>
            </div>
            <p>{item.description}</p>
          </a>
        ))}
      </section>
    </main>
  );
}
