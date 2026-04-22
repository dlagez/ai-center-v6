# Frontend

独立的 `React + Vite` 前端工程。

当前约束：

- 不修改 `src/api/static` 现有静态页面
- 不替换 FastAPI 现有页面路由
- 先在 `frontend/` 内完成模块化开发

本地开发：

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
cd frontend
npm run build
```

后续如果要接入后端，可以再决定：

- 将 `dist/` 发布到现有静态目录
- 或单独部署前端，并通过 API 访问后端
