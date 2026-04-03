# ai-center-v6

基于 LangGraph、FastAPI 和 LiteLLM 的 AI 应用骨架项目。

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

## LiteLLM 最简接入

LiteLLM 通过环境变量读取不同 provider 的密钥，项目里保留一个最薄封装：

- 配置文件：[settings.py](/D:/code-ai/ai-center-v6/src/config/settings.py)
- 模型封装：[llm.py](/D:/code-ai/ai-center-v6/src/models/llm.py)

业务代码可直接调用：

```python
from src.models.llm import chat_completion

answer = chat_completion(
    messages=[
        {"role": "system", "content": "你是企业AI中台助手"},
        {"role": "user", "content": "请解释一下RAG和Agentic RAG的区别"},
    ]
)

print(answer)
```

`.env` 最小示例：

```env
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
LLM_DEFAULT_MODEL=openai/gpt-4o
LLM_TIMEOUT=60
LLM_TEMPERATURE=0
```

如果接 OpenAI-compatible endpoint 或自建 vLLM，可额外设置：

```env
LLM_API_BASE=http://localhost:8000/v1
```

## 后续建议

- 在 `src/graphs/` 中实现 LangGraph 工作流
- 在 `src/models/` 中继续扩展 LiteLLM 多模型路由
- 在 `src/tools/` 中定义工具调用
- 在 `tests/` 中补充单元测试和集成测试
