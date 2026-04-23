import "./styles.css";

const NAV_ITEMS = [
  {
    title: "文件管理",
    path: "/file-manager",
    description: "统一上传、查看和删除文件记录，不触发解析，作为基础文件管理页面使用。",
  },
  {
    title: "PDF 预览",
    path: "/pdf-preview",
    description: "上传 PDF、查看文件列表，并使用原始 PDF 预览与高亮框调试。",
  },
  {
    title: "知识库管理",
    path: "/knowledge-base",
    description: "统一管理知识库内容、入库操作、检索测试和删除，作为基础管理页面使用。",
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
