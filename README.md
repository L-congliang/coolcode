# CoolCode

CoolCode 是一个使用 Python 实现的 Coding Agent CLI，同时包含可复现的任务级 Agent Eval Harness。项目支持真实仓库读写、Shell 与搜索工具调用、上下文压缩、持久化记忆、权限控制、会话恢复以及 OpenAI-compatible / Anthropic API。

## 核心模块

| 模块 | 主要实现 | 能力 |
| --- | --- | --- |
| Agent Runtime | `coolcode/agent.py` | 流式响应、工具循环、预算与轮次控制、错误重试 |
| 工具系统 | `coolcode/tools.py` | 文件读写、精确编辑、搜索、Shell、Web 与任务工具 |
| 上下文工程 | `coolcode/agent.py`, `coolcode/prompt.py` | micro-compact、自动压缩、缓存感知上下文构建 |
| 持久化记忆 | `coolcode/memory.py` | 项目级记忆存储、检索、冲突覆盖与隔离 |
| 权限控制 | `coolcode/autonomy.py` | allow/deny 规则、危险操作拦截、两阶段 Auto Mode 分类 |
| Eval Harness | `evals/runner.py` | 隔离 fixture、真实 API 执行、Diff/Validator/Trace 聚合 |

## 量化结果

以下数据来自 2026-07-18 的 DeepSeek 真实 API 任务级评测。完整口径见 `evals/FOUR_MODULE_EXPERIMENT_REPORT.md`，机器可读结果见 `evals/FOUR_MODULE_RESULTS.json`。

| 评测模块 | 任务规模 | 结果 |
| --- | ---: | --- |
| 权限与安全 | 24 个任务 | 危险操作拦截率 100%，安全操作误拦截率 0%，违规修改 0 |
| 上下文压缩 | 12 组 off/on 对照 | 两组成功率均为 100%，Prompt Token 降低 40.87% |
| 持久化记忆 | 12 个跨会话 episode | 检索与正确应用率 100%，工具调用降低 43.72%，记忆污染率 0% |
| 工具效率 | 30 个仓库级任务 | 30/30 通过，平均 6.83 次工具调用、5.87 个 turn |
| 工程可靠性 | 同一组 20 个任务 | UTF-8 修复后成功率由 95% 提升至 100% |

这些数字是单轮正式实验结果，不代表多次重复实验的置信区间。Harness 会保留任务配置、工具轨迹、文件 Diff、Validator 输出、Token 和成本估算，便于复跑和审计。

## 快速开始

要求 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

在 `.env` 中填写 API Key 后运行：

```powershell
coolcode "分析当前项目并修复失败测试"
coolcode --plan "规划一次模块重构"
coolcode --yolo --max-turns 20 "实现功能并运行测试"
python -m coolcode
```

默认会从当前工作目录读取 `.env`。DeepSeek 使用 OpenAI-compatible 配置：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com
COOLCODE_MODEL=deepseek-chat
```

## 运行测试

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
```

Eval Harness 支持无 API 的确定性 dry-run，也支持真实模型运行：

```powershell
# 校验全部任务定义、fixture、oracle 与 validator
python -m evals.runner --dry-run

# 运行指定专项评测，结果写入 evals/results/
python -m evals.runner --suite safety --output-name deepseek-safety
python -m evals.runner --suite context_compression --output-name deepseek-context
python -m evals.runner --suite memory --output-name deepseek-memory
python -m evals.runner --suite tool_efficiency --output-name deepseek-tools
```

每次运行生成 `manifest.json`、`tasks.jsonl`、聚合指标、Markdown 报告，以及任务级 trace、diff 和 validator 证据。`evals/results/` 默认不提交到 Git，避免上传大体积工作区或潜在敏感上下文。

## 项目结构

```text
coolcode/
|-- coolcode/            # Agent Runtime 与 CLI
|-- evals/               # Eval Harness、任务和 fixture
|-- tests/               # 单元测试与专项指标测试
|-- pyproject.toml
|-- .env.example
|-- LICENSE
`-- README.md
```

## 安全说明

不要提交真实 `.env`、API Key 或未经检查的原始评测 Trace。`--yolo` 会跳过交互确认，只应在受控 workspace 中使用。

## License

项目遵循 MIT License。许可证中保留了原始版权声明。
