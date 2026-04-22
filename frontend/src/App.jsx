const cards = [
  {
    title: "现有静态页面保持不动",
    body: "FastAPI 继续直接提供 src/api/static 下的 HTML 页面，当前功能入口不受影响。",
  },
  {
    title: "React 前端独立开发",
    body: "新界面在 frontend/ 内演进，先做模块化和组件化，再按页面逐步接管。",
  },
  {
    title: "后续再决定发布方式",
    body: "等功能稳定后，再选择是否把 Vite 构建产物发布到后端静态目录或单独部署。",
  },
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">React + Vite</p>
        <h1>AI Center V6 Frontend</h1>
        <p className="lead">
          当前阶段新增独立前端工程，不改动现有 <code>src/api/static</code> 页面和 FastAPI
          路由。
        </p>
      </section>

      <section className="card-grid">
        {cards.map((card) => (
          <article className="info-card" key={card.title}>
            <h2>{card.title}</h2>
            <p>{card.body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
