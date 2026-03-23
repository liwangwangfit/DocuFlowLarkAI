# DocuFlowLarkAI 项目上下文（2026-03-22）

## 1. 项目定位
DocuFlowLarkAI 是一个面向飞书/Lark 知识库迁移的桌面化工具，目标是让用户在无浏览器依赖的桌面体验下，完成本地文档到飞书知识空间的批量迁移、模板复用、质量校验与实时监控。

---

## 2. 当前版本已实现能力

### 2.1 实时查看
- WebSocket 实时推送任务进度、日志、吞吐曲线、文件状态。
- 监控面板支持成功/重复/失败统计和文件名明细弹窗。

### 2.2 模块管理与多次复用
- 模板管理支持新建、编辑、删除、节点维护。
- 支持 JSON 模板导入/导出（含文件选择器与保存路径选择）。
- 新建任务时可实时获取最新模板列表并复用。

### 2.3 大模型自动校验
- LLM 支持快速总结、挂载点决策、可选质量校验。
- 支持多提供商（DeepSeek/Kimi/OpenAI/Claude/Qwen/Ollama/Mock）。

### 2.4 无损上传
- 文件上传链路保持源文件不被改写。
- 支持知识库重名检测：重复文件自动标记并跳过上传。
- 上传与任务执行支持异步并发，且对共享状态加锁保证线程安全。

### 2.5 其他亮点
- 桌面模式：`pywebview` 启动，无浏览器依赖，即开即用。
- 动态并发：根据 CPU 与可用内存自动调整 worker 数量。
- 统一项目内弹窗：避免系统/浏览器原生弹窗造成体验割裂。
- OAuth 授权支持状态轮询与过期倒计时。
- 配置安全：敏感配置（`app_secret`、`api_key`、`cloud_api_key`）加密落盘，不明文存储。

---

## 3. 技术栈
- 后端：Python 3.11 + FastAPI + httpx + SQLAlchemy + loguru
- 前端：单页 HTML + Tailwind + ECharts + 原生 JavaScript
- 桌面封装：pywebview（Edge WebView2）
- 数据：SQLite（任务与模板数据）

---

## 4. 核心流程
```text
本地文件
  -> 任务创建
  -> 文件去重检查（知识库 + 当前任务）
  -> LLM 快速总结（可选）
  -> 飞书 Drive 导入
  -> 导入结果轮询
  -> LLM 节点决策（可选）
  -> 飞书 Wiki 挂载
  -> 实时推送状态到前端
```

---

## 5. 目录结构（当前）
```text
DocuFlowLarkAI/
├── backend/
│   ├── main.py                  # FastAPI 主应用
│   ├── desktop_app.py           # 桌面启动入口（pywebview）
│   ├── config.py                # 配置加载、敏感字段加解密
│   ├── core/
│   │   ├── feishu/              # OAuth / Drive / Wiki API
│   │   └── llm/                 # 模型调用与决策逻辑
│   ├── models/                  # 模板与数据库模型
│   └── utils/                   # 日志、系统资源、并发计算
├── frontend/
│   └── index.html               # 单页前端
├── config/
│   ├── feishu.yaml
│   ├── llm.yaml
│   └── mineru.yaml
├── data/                        # 运行时数据（缓存、导出、日志）
├── scripts/                     # 启动/安装脚本
├── tests/                       # 自动化测试
└── README.md                    # 多语言说明文档
```

---

## 6. 关键 API（节选）

### 配置与安全
- `GET /api/config`：读取配置状态（不返回明文密钥）
- `POST /api/config`：更新配置（敏感字段加密写入）
- `POST /api/config/clear`：清空敏感配置并清除授权状态
- `POST /api/feishu/credentials/test`：测试 App ID / App Secret 有效性

### OAuth
- `GET /api/auth/status`
- `GET /api/auth/url`
- `POST /api/auth/exchange`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`

### 模板管理
- `GET /api/templates`
- `POST /api/templates`
- `PUT /api/templates/{id}`
- `DELETE /api/templates/{id}`
- `POST /api/templates/import`
- `GET /api/templates/{id}/export`

### 任务与上传
- `POST /api/tasks`
- `POST /api/tasks/{id}/upload`
- `POST /api/tasks/{id}/start`
- `POST /api/tasks/{id}/cancel`
- `DELETE /api/tasks/{id}`

---

## 7. 配置说明

### `config/feishu.yaml`
```yaml
app_id: ''
app_secret: ''
```

### `config/llm.yaml`
```yaml
providers:
  deepseek:
    enabled: false
    api_key: ''
```

> 当用户输入真实密钥并保存后，敏感字段会以 `enc:v1:...` 形式加密存储。

---

## 8. 启动与测试

### 启动（Windows）
```bat
scripts\start.bat
```

### 仅启动后端
```bat
scripts\start_backend.bat
```

### 测试
```bash
pytest tests -q
```

---

## 9. 当前注意事项
- `data/cache`、`data/logs`、`data/exports` 属于运行时目录，不建议纳入发布包。
- 日志建议避免记录任何 token 片段（后续可继续收敛日志策略）。
- `backend/main_new.py` 为历史文件，当前主入口为 `backend/main.py`。
