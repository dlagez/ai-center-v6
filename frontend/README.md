# Frontend

独立的 `React + Vite` 前端工程。

当前约束：

- 不修改 `src/api/static` 现有静态页面
- 不替换 FastAPI 现有页面路由
- 先在 `frontend/` 内完成模块化开发

## 开发命令

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

## 目录设计

建议后续按下面的结构扩展：

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── app/
    │   ├── router/
    │   ├── providers/
    │   └── store/
    ├── pages/
    │   ├── excel-update/
    │   │   ├── index.jsx
    │   │   ├── components/
    │   │   └── hooks/
    │   └── excel-update-tasks/
    │       ├── index.jsx
    │       ├── components/
    │       └── hooks/
    ├── components/
    │   ├── ui/
    │   └── business/
    ├── services/
    │   ├── api/
    │   └── adapters/
    ├── hooks/
    ├── utils/
    ├── constants/
    ├── assets/
    └── styles/
```

## 分层说明

### `src/app/`

放应用级能力，只放全局配置，不放具体业务页面逻辑。

建议内容：

- `router/`：路由配置
- `providers/`：全局上下文、主题、请求客户端注入
- `store/`：全局状态，如果后面确实需要

### `src/pages/`

按页面或功能域拆分，是后续最主要的开发目录。

规则：

- 一个页面一个目录
- 页面目录下放该页面自己的 `components/`、`hooks/`、样式和局部工具
- 页面入口统一使用 `index.jsx`

例如：

- `pages/excel-update/`：Excel 更新主页面
- `pages/excel-update-tasks/`：任务列表页面

如果后面页面更多，继续按业务域扩展，不要把所有页面组件都堆到全局 `components/`。

### `src/components/`

放跨页面复用组件，不放只被单个页面使用的局部组件。

建议继续分两层：

- `ui/`：纯展示组件，如按钮、弹窗、表格容器、表单块
- `business/`：跨页面复用的业务组件，如文件上传卡片、任务状态面板

判断标准：

- 只在一个页面用：放对应 `pages/<page>/components/`
- 两个及以上页面复用：放 `src/components/`

### `src/services/`

放接口访问和数据适配逻辑，不要把 `fetch` 直接散落在页面组件里。

建议：

- `api/`：按后端资源分文件，例如 `excelUpdateApi.js`
- `adapters/`：把后端返回结构转换成前端页面更好用的数据结构

### `src/hooks/`

放跨页面通用 hooks。

例如：

- `useRequest`
- `useDebounce`
- `usePagination`

如果 hook 只服务某个页面，就放到对应页面目录下的 `hooks/`。

### `src/utils/`

放纯函数工具，要求无副作用、易测试。

例如：

- 日期格式化
- 文件大小格式化
- 下载文件名处理

### `src/constants/`

放常量配置，例如：

- 路由路径
- 枚举值
- 默认分页参数

### `src/assets/`

放图片、图标、静态素材。

如果某个页面专属资源非常强，也可以放在对应页面目录内，避免全局目录膨胀。

### `src/styles/`

放全局样式能力：

- `reset.css`
- `variables.css`
- `global.css`

页面专属样式优先就近放在页面目录中。

## 页面扩展规则

后续新增前端页面时，按这个顺序放文件：

1. 在 `src/pages/` 下新建页面目录
2. 页面私有组件放到该目录的 `components/`
3. 页面私有 hooks 放到该目录的 `hooks/`
4. 页面调用的接口整理到 `src/services/api/`
5. 多页面复用的组件再上提到 `src/components/`

示例：

```text
src/pages/excel-update/
├── index.jsx
├── components/
│   ├── UploadPanel.jsx
│   └── ResultPreview.jsx
├── hooks/
│   └── useExcelUpdateForm.js
└── styles.css
```

## 当前阶段建议

现阶段项目刚起步，建议按下面的节奏推进：

1. 先把 `excel-update` 页面迁到 `src/pages/excel-update/`
2. 再迁 `excel-update-tasks`
3. 过程中识别哪些组件值得抽到 `src/components/`
4. 最后再补路由、全局状态和统一请求封装

这样比一开始就铺太多目录更稳，也更容易保持结构干净。

## 后续接入方式

后续如果要接入后端，可以再决定：

- 将 `dist/` 发布到现有静态目录
- 或单独部署前端，并通过 API 访问后端
