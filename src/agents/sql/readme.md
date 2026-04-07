这版 SQL agent 的流程是“先看库，再看表，再生成 SQL，再校验，再执行，再回答”。

核心链路在：
- [graph.py](/D:/code-ai/ai-center-v6/src/agents/sql/graph.py)
- [nodes.py](/D:/code-ai/ai-center-v6/src/agents/sql/nodes.py)
- [service.py](/D:/code-ai/ai-center-v6/src/agents/sql/service.py)

完整流程如下。

**1. 接收问题和数据库路径**
你调用：
```powershell
python scripts\sql_agent.py "How many open jobs do we have by department?"
```

脚本会请求：
```http
POST /agents/sql
```

服务层入口是：
[service.py](/D:/code-ai/ai-center-v6/src/agents/sql/service.py)

这里会做几件事：
- 校验 `question`
- 取 `db_path`
- 如果数据库文件不存在，就自动创建空的 SQLite 文件
- 把初始状态喂给 LangGraph

初始状态大致是：
- `question`
- `db_path`
- `max_rows`
- `max_retries`

**2. 先列出数据库里有哪些表**
第一个节点是：
`list_database_tables`

对应：
[list_database_tables](/D:/code-ai/ai-center-v6/src/agents/sql/nodes.py)

这里直接查 SQLite 的系统表：
```sql
SELECT name
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
ORDER BY name
```

这一步不靠 LLM，是程序直接拿真实表名。  
比如会得到：
- `departments`
- `employees`
- `jobs`
- `candidates`
- `attendance`
- `performance_reviews`
- `payroll`

**3. 让模型从所有表里挑相关表**
第二个节点是：
`select_relevant_tables`

这里才第一次调用模型。  
它会把：
- 用户问题
- 所有表名

一起发给 LLM，让它只返回 JSON：
```json
{"tables": ["jobs", "departments"]}
```

比如问题是：
`How many open jobs do we have by department?`

模型会倾向选：
- `jobs`
- `departments`

这一步的目的，是缩小后面要给模型看的 schema 范围。  
否则把全库 schema 全塞进去，生成 SQL 会更容易漂。

**4. 读取这些表的真实 schema**
第三个节点是：
`load_selected_schema`

这里再次不靠 LLM，而是直接查 SQLite 的 `sqlite_master`，拿建表语句。

例如会拿到：
```sql
CREATE TABLE jobs (...)
CREATE TABLE departments (...)
```

然后拼成一段 `schema_text`，给后面的 SQL 生成节点用。

**5. 基于 question + schema 生成 SQL**
第四个节点是：
`generate_query`

这里把两样东西给模型：
- 用户问题
- 真实 schema

提示词要求它：
- 只写一条只读 SQLite 查询
- 不要解释
- 不要 Markdown
- 不要写修改数据的 SQL

比如它会生成：
```sql
SELECT d.department_name, COUNT(*) AS open_job_count
FROM departments d
JOIN jobs j ON d.department_id = j.department_id
WHERE j.job_status = 'open'
GROUP BY d.department_name
```

这一步就是“SQL 是怎么生成的”最核心的一步：  
不是模型凭空猜，而是“拿着真实 schema 按提示词生成”。

**6. 再让模型检查一遍 SQL**
第五个节点是：
`check_query`

这一步是从官方 SQL agent 示例借来的关键思想。  
不是生成完就跑，而是再过一遍“审 SQL”的模型节点。

这里会把：
- 用户问题
- schema
- 刚生成的 SQL

再发给 LLM，让它做这些检查：
- 表名是不是对的
- 列名是不是对的
- SQLite 语法是不是对的
- 聚合是不是合理
- 是否需要 `LIMIT`

如果没问题，它会原样返回。  
如果有问题，它会返回修正后的 SQL。

所以你的 SQL 不是“一次生成”，而是：
- 第一次生成
- 第二次校验/修正

**7. 执行 SQL**
第六个节点是：
`run_sql_query`

这一步是程序真实执行，不靠模型。

执行前还会做一层安全限制：
- 只允许 `SELECT` 或 `WITH`
- 禁止 `INSERT/UPDATE/DELETE/DROP/ALTER/...`

所以这是只读 agent，不会改库。

然后用 sqlite3 去跑，拿回：
- 查询结果 `rows`
- 或错误 `query_error`

**8. 如果执行失败，就回去重生成**
如果 SQL 执行失败，比如：
- 列名写错
- 表名写错
- join 错了

graph 不会立刻结束，而是按这个逻辑走：
- 记录错误信息
- 把错误塞回 `generate_query`
- 再生成一次 SQL
- 最多重试 `max_retries`

这部分在图里是一个循环。

也就是说，流程不是直线，而是：
- 生成 SQL
- 执行失败
- 带着错误重新生成 SQL
- 再执行

这是 LangGraph 官方 SQL agent 示例里最重要的设计点之一。

**9. 基于结果生成自然语言答案**
最后一个节点是：
`generate_answer`

这里把这些内容给模型：
- 用户问题
- 最终 SQL
- 查询结果
- 查询错误

然后让它生成最终答案。

例如：
- 如果查到了结果，就总结结果
- 如果没查到，明确说没有数据
- 如果 SQL 失败，也会说明失败原因

所以最终你拿到的不是只是一条 SQL，而是：
- `sql_query`
- `rows`
- `answer`
- `error`

**10. 空库的特殊处理**
如果数据库刚创建，还没有表，现在不会乱生成 SQL。

流程会变成：
- 发现没有表
- 不再走 SQL 生成/执行
- 直接返回：
  - `sql_query=""`
  - `rows=[]`
  - `error="The database has no tables yet..."`
  - `answer="请先建表导入数据"`

这是我后来专门补的保护。

**一句话总结 SQL 是怎么生成的**
不是“模型直接猜一条 SQL 就执行”，而是：

1. 程序先读取真实表名
2. 模型选择相关表
3. 程序读取这些表的真实 schema
4. 模型基于 question + schema 生成 SQL
5. 模型再校验一次 SQL
6. 程序执行 SQL
7. 如果报错，把错误反馈给模型重试
8. 最后模型基于结果生成答案

所以这其实是一个“LLM 规划 + 程序执行 + 错误反馈重试”的流程。

如果你要，我下一步可以给你画成一张 Mermaid 流程图。