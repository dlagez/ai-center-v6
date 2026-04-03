# ai-center-v6

基于 LangGraph 和 FastAPI 的 AI 应用骨架项目。

## 目录结构

```text
ai-center-v6
├─ src/
│  ├─ config/
│  ├─ graphs/
│  ├─ models/
│  ├─ tools/
│  ├─ knowledge/
│  ├─ observability/
│  ├─ evals/
│  └─ api/
├─ tests/
├─ scripts/
├─ .env.example
├─ pyproject.toml
├─ langgraph.json
└─ README.md
```

## 快速开始

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.api.app:app --reload
```

## 后续建议

- 在 `src/config/` 中扩展配置加载逻辑
- 在 `src/graphs/` 中实现 LangGraph 工作流
- 在 `src/models/` 中封装模型客户端
- 在 `src/tools/` 中定义工具调用
- 在 `tests/` 中补充单元测试和集成测试

