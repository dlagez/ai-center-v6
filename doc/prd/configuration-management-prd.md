# 配置管理 PRD

## 1. 文档信息

**文档名称**：AI 中台配置管理 PRD
**适用项目**：基于 LangChain / LangGraph 的 AI 中台
**当前阶段**：MVP / 第一阶段
**作者**：项目组
**版本**：V1.0

---

## 2. 背景与目标

本项目第一阶段主要建设以下模块：

* Agent 编排与运行层
* 模型与工具抽象层
* 知识库与检索层
* 观测、评测、部署层

随着模块逐步落地，系统会出现越来越多的配置项，包括但不限于：

* LLM 与 Embedding 接入配置
* LangGraph 运行配置
* LangSmith tracing / evaluation 配置
* 向量库配置
* 检索参数配置
* 工具开关与工具参数配置
* 环境隔离配置
* 业务运行参数配置

如果配置管理方式不统一，后续会快速出现以下问题：

1. 配置来源混乱，环境变量、代码常量、JSON 文件、数据库配置并存；
2. 不同模块读取配置方式不一致，维护成本高；
3. 缺乏类型校验，配置错误只能在运行时暴露；
4. 本地、测试、生产环境切换困难；
5. secret 与普通配置混放，存在泄漏风险；
6. 后续多租户、多应用、多 Agent 场景下无法平滑扩展。

因此，本 PRD 的目标是定义一套**简单、统一、可扩展**的配置管理方案，服务于当前 MVP，并为后续平台化扩展预留边界。

---

## 3. 产品目标

### 3.1 总体目标

构建一套统一的配置管理机制，满足以下要求：

* 支持本地开发、测试、生产环境切换；
* 支持类型安全与启动时校验；
* 支持环境变量覆盖；
* 支持 Secret 与普通配置分离；
* 支持模块化配置组织；
* 支持 LangGraph / LangSmith / LLM / RAG 场景；
* 保持实现简单，不引入过重的配置系统。

### 3.2 第一阶段目标

第一阶段仅解决“应用级配置管理”问题，不解决平台级动态配置中心问题。
即：

* 配置以**代码 + `.env` + `langgraph.json`** 为主；
* 不引入 Apollo / Nacos / Consul / ZooKeeper 等远程配置中心；
* 不做数据库动态配置后台；
* 不做租户级在线配置编辑界面。

---

## 4. 非目标

以下内容不在本阶段范围内：

1. 不建设可视化配置后台；
2. 不支持在线热更新所有配置；
3. 不实现多租户配置隔离；
4. 不实现配置审批流；
5. 不实现数据库持久化配置中心；
6. 不实现复杂的灰度配置分发；
7. 不实现运行时动态修改模型路由策略。

上述能力将在后续平台层建设时再单独设计。

---

## 5. 设计原则

### 5.1 简单优先

优先采用最少的配置载体与最少的依赖，避免一开始引入过重框架。

### 5.2 统一入口

所有业务代码只能通过统一配置入口读取配置，不允许模块内部散落读取 `os.getenv()`。

### 5.3 类型安全

所有配置项必须有明确的数据类型、默认值策略和校验规则。

### 5.4 环境隔离

本地开发、测试、生产环境必须可以明确区分，并支持独立配置。

### 5.5 Secret 分离

API Key、数据库密码、Access Token 等敏感信息必须与普通配置逻辑隔离。

### 5.6 可扩展

当前只做应用级配置，但后续要能平滑升级到：

* 多环境
* 多应用
* 多租户
* 动态配置中心
* 配置可视化管理

---

## 6. 总体方案

本项目第一阶段采用以下配置管理方案：

### 6.1 配置技术选型

采用：

* **Pydantic Settings**：作为应用内部配置管理框架
* **`.env` 文件**：作为本地开发配置载体
* **环境变量**：作为部署环境配置载体
* **`langgraph.json`**：作为 LangGraph 应用声明与运行入口配置文件

### 6.2 配置边界划分

#### A. 应用内部配置

由 `Pydantic Settings` 管理，负责：

* 应用基础配置
* 模型配置
* Embedding 配置
* 检索配置
* 向量库配置
* 工具配置
* LangSmith 配置
* Checkpoint / Memory 后端配置

#### B. LangGraph 运行配置

由 `langgraph.json` 管理，负责：

* graph 入口声明
* dependencies 声明
* 环境变量文件声明
* LangGraph 运行相关元信息

### 6.3 不采用的方案

本阶段不采用：

* 手写配置加载器
* YAML + 自定义解析逻辑
* Dynaconf
* Hydra
* 远程配置中心

原因：当前阶段以“快速落地、降低复杂度”为主，过重方案会拖慢开发。

---

## 7. 配置优先级规则

系统配置读取优先级定义如下：

### 7.1 优先级从高到低

1. 运行环境注入的环境变量
2. `.env` 文件
3. `settings.py` 中定义的默认值

### 7.2 规则说明

* 生产环境应优先使用系统环境变量或容器环境变量；
* 本地开发环境可使用 `.env`；
* 默认值仅用于非关键配置；
* 关键配置不得依赖默认值静默运行。

### 7.3 关键配置要求

以下配置必须显式提供，缺失时启动失败：

* LLM API Key
* Embedding API Key（如独立）
* 向量库连接信息
* LangSmith API Key（若开启 tracing）
* 默认模型名
* 默认 Embedding 模型名

---

## 8. 项目目录设计

建议目录如下：

```text
ai-platform/
├─ src/
│  ├─ config/
│  │  ├─ settings.py
│  │  ├─ logging.py
│  │  └─ __init__.py
│  ├─ graphs/
│  ├─ models/
│  ├─ tools/
│  ├─ knowledge/
│  ├─ observability/
│  ├─ evals/
│  └─ api/
├─ .env
├─ .env.example
├─ langgraph.json
├─ pyproject.toml
└─ docs/
   └─ prd/
      └─ configuration-management-prd.md
```

---

## 9. 配置模块设计

## 9.1 配置模块职责

`src/config/settings.py` 是配置系统唯一入口，负责：

* 读取配置
* 类型校验
* 默认值管理
* 暴露统一 settings 对象
* 为各模块提供结构化配置访问方式

业务模块禁止自行直接读取环境变量。

---

## 9.2 配置分层结构

建议按以下配置域组织：

### 1）AppConfig

用于应用基础配置：

* app_name
* app_env
* debug
* log_level

### 2）LLMConfig

用于大模型接入：

* provider
* model_name
* base_url
* api_key
* timeout
* max_tokens
* temperature

### 3）EmbeddingConfig

用于 embedding 模型接入：

* provider
* model_name
* base_url
* api_key
* dimension

### 4）RerankerConfig

用于 reranker 配置：

* enabled
* provider
* model_name
* top_n

### 5）VectorStoreConfig

用于向量库配置：

* backend
* host
* port
* collection_name
* api_key
* namespace

### 6）RetrievalConfig

用于检索参数：

* top_k
* score_threshold
* hybrid_enabled
* rerank_enabled
* chunk_size
* chunk_overlap

### 7）ToolConfig

用于工具层配置：

* sql_enabled
* python_enabled
* search_enabled
* http_enabled
* tool_timeout

### 8）MemoryConfig

用于 session / long-term memory 配置：

* checkpointer_backend
* memory_backend
* thread_ttl
* session_ttl

### 9）LangSmithConfig

用于 tracing / eval：

* enabled
* api_key
* project
* endpoint

---

## 10. 配置命名规范

### 10.1 环境变量命名规范

统一使用大写下划线风格，按领域前缀区分，例如：

```env
APP_NAME=ai-platform
APP_ENV=dev
APP_DEBUG=true

LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1
LLM_BASE_URL=
LLM_API_KEY=

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_API_KEY=

VECTORSTORE_BACKEND=pgvector
VECTORSTORE_HOST=localhost
VECTORSTORE_PORT=5432
VECTORSTORE_COLLECTION=default_knowledge

RETRIEVAL_TOP_K=5
RETRIEVAL_SCORE_THRESHOLD=0.2
RETRIEVAL_HYBRID_ENABLED=true

TOOL_SQL_ENABLED=false
TOOL_PYTHON_ENABLED=true
TOOL_SEARCH_ENABLED=true

LANGSMITH_ENABLED=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=ai-platform-dev
```

### 10.2 命名要求

* 同一领域配置必须使用同一前缀；
* 不允许出现含义模糊的变量名，如 `MODEL`、`HOST`、`KEY`；
* Secret 字段统一显式命名为 `*_API_KEY`、`*_PASSWORD`、`*_TOKEN`。

---

## 11. 配置加载流程

## 11.1 启动流程

系统启动时执行以下步骤：

1. 读取运行环境变量；
2. 读取 `.env`；
3. 加载 `settings.py` 中的配置模型；
4. 进行字段级类型校验；
5. 进行跨字段业务校验；
6. 生成全局只读 settings 对象；
7. 应用启动。

## 11.2 启动失败策略

出现以下情况时必须启动失败：

* 必填配置缺失；
* 配置类型错误；
* 配置值不在允许范围；
* 组合配置非法，例如：

  * 启用了 tracing，但未提供 LangSmith API Key；
  * 启用了 rerank，但未配置 reranker 模型；
  * 向量库后端已配置，但 host/port 缺失。

---

## 12. Secret 管理要求

## 12.1 Secret 范围

包括但不限于：

* LLM API Key
* Embedding API Key
* LangSmith API Key
* 向量库密码
* 数据库密码
* 第三方工具 Token

## 12.2 管理原则

* Secret 不允许硬编码在代码中；
* Secret 不允许提交到 Git；
* `.env` 必须加入 `.gitignore`；
* 仓库中只保留 `.env.example`；
* 生产环境 Secret 必须通过环境变量、容器注入或 Secret Manager 提供。

## 12.3 日志要求

* 日志中禁止输出完整 Secret；
* 配置打印时必须脱敏；
* 出错信息中不得回显敏感值。

---

## 13. 不同环境的配置策略

## 13.1 环境枚举

第一阶段支持以下环境：

* `dev`
* `test`
* `prod`

## 13.2 环境差异建议

### dev

* 允许 `.env`
* 允许 debug
* 可使用本地向量库或本地数据库
* tracing 可选开启

### test

* 接近生产配置
* 禁止随意使用本地 mock key
* 强制开启更多日志与 tracing
* 便于集成测试与回归评测

### prod

* 禁止依赖本地 `.env`
* Secret 必须由外部注入
* 默认关闭 debug
* 严格控制日志级别
* 所有关键配置必须显式声明

---

## 14. 与 LangGraph 的关系

## 14.1 `langgraph.json` 的职责

`langgraph.json` 负责定义：

* graph 的入口模块
* 项目依赖
* 使用的环境文件
* LangGraph 运行元信息

## 14.2 与应用配置的边界

* `langgraph.json` 不承担业务配置中心职责；
* 业务模块仍通过 `settings.py` 读取配置；
* `langgraph.json` 更像是 LangGraph 应用清单，而不是业务参数仓库。

## 14.3 设计要求

后续所有 graph 在运行时若需要模型、工具、检索参数，必须从统一 settings 获取，不允许在 graph 文件中直接散落写死参数。

---

## 15. 与各模块的集成要求

## 15.1 Agent 编排与运行层

需要读取：

* 默认模型配置
* checkpoint backend
* memory backend
* tool 开关
* graph 运行参数

要求：

* graph 节点内不得硬编码模型名；
* checkpoint 后端切换必须通过配置完成；
* tool 是否可用必须通过配置控制。

## 15.2 模型与工具抽象层

需要读取：

* provider
* model_name
* base_url
* api_key
* timeout
* structured output 参数

要求：

* 模型工厂必须只依赖 settings；
* 不同 provider 切换时不修改业务代码。

## 15.3 知识库与检索层

需要读取：

* parser 参数
* chunk 配置
* embedding 配置
* vector store 配置
* retrieval 参数
* rerank 参数

要求：

* chunk_size、top_k、score_threshold 可配置；
* 不同向量库后端通过配置切换；
* 检索策略升级时优先扩展配置，不直接改死逻辑。

## 15.4 观测、评测、部署层

需要读取：

* LangSmith 开关
* project 名称
* tracing endpoint
* eval 数据集路径
* report 输出路径

要求：

* tracing 与 eval 能通过配置独立开关；
* 测试环境与生产环境项目名分离；
* 运行时支持打印配置摘要，但必须脱敏。

---

## 16. 配置变更策略

## 16.1 第一阶段策略

第一阶段采用“重启生效”模式：

* 修改 `.env`
* 修改环境变量
* 修改 `langgraph.json`

均通过服务重启后生效。

## 16.2 不支持内容

本阶段不支持：

* 运行时热加载
* UI 在线修改立即生效
* 分布式配置广播

原因：避免引入复杂性与一致性问题。

---

## 17. 日志与可观测性要求

配置系统本身需要具备基础可观测能力。

### 17.1 启动日志

启动时输出配置摘要，包括：

* 当前环境
* 当前默认 provider
* 当前默认模型
* 向量库后端
* tracing 是否开启

### 17.2 脱敏要求

以下字段必须脱敏显示：

* API Key
* 密码
* Token
* Secret URL 中的认证参数

### 17.3 错误输出

配置错误必须输出：

* 错误字段名
* 期望类型或规则
* 当前环境
* 修复建议

---

## 18. 测试要求

配置管理模块必须具备以下测试：

## 18.1 单元测试

覆盖：

* 默认值是否正确
* `.env` 是否能正确加载
* 环境变量覆盖是否生效
* 必填项缺失是否报错
* 类型错误是否报错

## 18.2 集成测试

覆盖：

* dev/test/prod 三环境切换
* LangSmith 开关逻辑
* 检索参数加载是否正确
* 模型工厂是否正确读取配置

## 18.3 安全测试

覆盖：

* Secret 不输出到日志
* `.env` 不被误提交
* 错误栈中不泄漏敏感值

---

## 19. 验收标准

本 PRD 对应的配置管理能力，验收标准如下：

### 19.1 功能验收

1. 项目存在统一配置入口；
2. 各模块通过统一 settings 读取配置；
3. 支持 `.env` 与环境变量；
4. 支持 dev/test/prod 区分；
5. 支持类型校验与启动失败；
6. Secret 不硬编码、不进 Git；
7. LangGraph 入口配置与业务配置边界清晰。

### 19.2 工程验收

1. 配置目录结构清晰；
2. `.env.example` 完整；
3. `settings.py` 模型分层清晰；
4. 有基本单元测试；
5. 日志输出可读且脱敏。

---

## 20. 里程碑建议

### M1：基础配置系统落地

交付内容：

* `settings.py`
* `.env.example`
* `.gitignore`
* `langgraph.json`
* 配置单元测试

### M2：接入模型与检索模块

交付内容：

* 模型工厂接入 settings
* embedding 接入 settings
* vector store 接入 settings
* retrieval 参数接入 settings

### M3：接入观测与评测

交付内容：

* LangSmith 开关配置
* tracing 初始化
* eval runner 配置化

### M4：为后续平台化预留接口

交付内容：

* 配置分层抽象
* 预留动态配置源接口
* 预留多租户扩展点

---

## 21. 后续演进路线

第一阶段完成后，配置系统可按以下方向演进：

### 21.1 第二阶段

* 支持配置来源抽象
* 支持数据库配置
* 支持租户级配置隔离
* 支持应用级配置覆盖

### 21.2 第三阶段

* 支持可视化配置后台
* 支持配置审批与发布
* 支持灰度配置
* 支持动态刷新部分配置

### 21.3 第四阶段

* 接入远程配置中心
* 接入 Secret Manager
* 支持多集群环境统一管理

---

## 22. 实施建议

第一阶段建议严格采用以下规则：

1. 所有配置统一进 `settings.py`；
2. 所有业务代码禁止直接 `os.getenv()`；
3. 所有新模块接入时先补配置模型；
4. 所有关键参数优先做成配置项，不要写死；
5. 所有 Secret 通过 `.env` 或环境变量注入；
6. `langgraph.json` 只承担 LangGraph 应用声明职责，不承担业务配置中心职责。

---

## 23. 附录：建议的最小配置项清单

```env
APP_NAME=ai-platform
APP_ENV=dev
APP_DEBUG=true
LOG_LEVEL=INFO

LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1
LLM_BASE_URL=
LLM_API_KEY=
LLM_TIMEOUT=60
LLM_TEMPERATURE=0

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=

VECTORSTORE_BACKEND=pgvector
VECTORSTORE_HOST=localhost
VECTORSTORE_PORT=5432
VECTORSTORE_COLLECTION=default_knowledge
VECTORSTORE_API_KEY=

RETRIEVAL_TOP_K=5
RETRIEVAL_SCORE_THRESHOLD=0.2
RETRIEVAL_HYBRID_ENABLED=true
RETRIEVAL_RERANK_ENABLED=false
RETRIEVAL_CHUNK_SIZE=800
RETRIEVAL_CHUNK_OVERLAP=150

TOOL_SQL_ENABLED=false
TOOL_PYTHON_ENABLED=true
TOOL_SEARCH_ENABLED=true
TOOL_HTTP_ENABLED=true
TOOL_TIMEOUT=30

MEMORY_CHECKPOINTER_BACKEND=memory
MEMORY_BACKEND=memory
MEMORY_THREAD_TTL=86400
MEMORY_SESSION_TTL=86400

LANGSMITH_ENABLED=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=ai-platform-dev
LANGSMITH_ENDPOINT=
```

---

如果你愿意，我下一条直接给你补上这份 PRD 对应的：
**`settings.py` 类骨架 + `.env.example` + `langgraph.json` 示例**，这样你可以直接开始建项目。
