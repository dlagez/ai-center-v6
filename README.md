# ai-center-v6

基于 LangGraph、FastAPI、LiteLLM、Docling 和 Qdrant 的 AI 应用骨架项目。

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
source .venv/bin/activate
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
        {"role": "user", "content": "请解释一下 RAG 和 Agentic RAG 的区别"},
    ]
)

print(answer)
```

`.env` 最小示例：

```env
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
DASHSCOPE_API_KEY=your-dashscope-key
LLM_DEFAULT_MODEL=openai/gpt-4o
LLM_TIMEOUT=60
LLM_TEMPERATURE=0
```

如果接 OpenAI-compatible endpoint 或自建 vLLM，可额外设置：

```env
LLM_API_BASE=http://localhost:8000/v1
```

### 阿里云 DashScope / Qwen

LiteLLM 可直接使用 `dashscope/<model>` 模型名。例如：

```env
DASHSCOPE_API_KEY=your-dashscope-key
LLM_DEFAULT_MODEL=dashscope/qwen-plus
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

新加坡地域可改为：

```env
DASHSCOPE_API_BASE=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

项目里的 [llm.py](/D:/code-ai/ai-center-v6/src/models/llm.py) 已支持：

- 通用覆盖：`LLM_API_BASE`
- DashScope 专用：`DASHSCOPE_API_BASE`

## Docling 最简接入

知识库层已经接入 Docling，统一把文档转换为 Markdown 文本：

- 解析入口：[parser.py](/D:/code-ai/ai-center-v6/src/knowledge/parser.py)
- 数据结构：[schemas.py](/D:/code-ai/ai-center-v6/src/knowledge/schemas.py)
- 简单分块：[chunker.py](/D:/code-ai/ai-center-v6/src/knowledge/chunker.py)
- 导入脚本：[ingest_docs.py](/D:/code-ai/ai-center-v6/scripts/ingest_docs.py)

示例：

```python
from pathlib import Path

from src.knowledge.parser import DoclingParser

parser = DoclingParser()
parsed = parser.parse(Path("data/raw/example.pdf"))

print(parsed.text[:2000])
```

## Qdrant 最简接入

向量库已接入 Qdrant 本地模式，默认使用磁盘持久化路径：

- 存储入口：[store.py](/D:/code-ai/ai-center-v6/src/knowledge/store.py)
- 写入入口：[indexer.py](/D:/code-ai/ai-center-v6/src/knowledge/indexer.py)
- 检索入口：[retriever.py](/D:/code-ai/ai-center-v6/src/knowledge/retriever.py)

最小配置：

```env
QDRANT_PATH=./data/qdrant
QDRANT_COLLECTION=default_knowledge
EMBEDDING_DIMENSION=1536
```

本地模式使用 `QdrantClient(path=...)`，开发阶段不需要单独启动 Qdrant 服务。

## 常用脚本

文档入库：

```powershell
.venv\Scripts\python scripts\build_index.py data/raw
```

知识检索：

```powershell
.venv\Scripts\python scripts\search_knowledge.py "这套方案的基本思路是什么？" --limit 5
```

RAG 问答：

```powershell
.venv\Scripts\python scripts\rag_answer.py "这套方案的基本思路是什么？" --limit 5
```

Agentic RAG 问答：

```powershell
.venv\Scripts\python scripts\agentic_rag_answer.py "这套方案的基本思路是什么？" --limit 5
```

Excel 回写安全评估：

```powershell
.venv\Scripts\python scripts\assess_excel_roundtrip.py original.xlsx roundtrip.xlsx
```

## 后续建议

- 在 `src/graphs/` 中实现 LangGraph 工作流
- 在 `src/models/` 中继续扩展 LiteLLM 多模型路由
- 在 `src/tools/` 中定义工具调用
- 在 `tests/` 中补充单元测试和集成测试
## Langfuse Cloud

Set these values in `.env` to enable Langfuse Cloud tracing:

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Current tracing coverage:

- `POST /knowledge/ingest`
- `POST /knowledge/search`
- `POST /rag/agentic-answer`
- LiteLLM chat generations
- LiteLLM embeddings
- Agentic RAG graph nodes

Successful API responses now include `trace_id` and `trace_url` when Langfuse is enabled.

## Vision Chat

Qwen vision models can be used through Bailian's OpenAI-compatible endpoint with mixed text and image content.

Minimal `.env` settings:

```env
DASHSCOPE_API_KEY=your-dashscope-key
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_VISION_MODEL=dashscope/qwen-vl-plus-latest
```

API:

```text
POST /models/vision/chat
```

Request with a public image URL:

```json
{
  "prompt": "Describe the image",
  "image_url": "https://example.com/demo.jpg",
  "model": "qwen-vl-max-latest"
}
```

Request with a local image path on the server:

```json
{
  "prompt": "Describe the image",
  "image_path": "D:/code-ai/ai-center-v6/data/demo.png"
}
```
