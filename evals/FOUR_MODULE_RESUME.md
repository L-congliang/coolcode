# CoolCode：面向 Harness Engineering 的 Coding Agent CLI

技术栈：Python、DeepSeek API、OpenAI-compatible API、Custom Agent Runtime、AsyncIO、CLI、unittest、JSONL Trace、Diff Analysis

项目概述：面向真实代码仓库任务实现 Coding Agent CLI，支持多轮工具调用、流式输出、上下文压缩、持久化记忆、权限控制、文件编辑与 shell 执行，并构建任务级 Agent Eval Harness 对系统能力进行量化评测。

- Agent Eval Harness：使用 Python 构建 repo-level 任务评测系统，自动完成 workspace 隔离、真实模型调用、文件 diff、validator、工具轨迹、token/耗时/成本统计与失败分类；扩展 82 个专项任务，在校正后的 30 个 bugfix、测试生成、重构和多文件任务上达到 100% validator 通过率，平均 6.83 次工具调用、5.87 turns。

- 上下文压缩：实现 tool result budgeting、stale result snip、microcompact 与 auto-compact 多层压缩机制；在 12 组 compression off/on 长上下文配对任务中保持 100% 成功率，将累计 prompt token 从 162.24 万降至 95.93 万，降低 40.87%，记录 64 次压缩事件并从历史中移除 72.06 万字符。

- 持久化记忆：实现基于文件索引、semantic side query 与异步 prefetch 的跨任务记忆检索；在 12 个 episode、48 个独立 Agent 上下文中，memory on 的检索命中率和正确应用率均为 100%，冲突记忆污染率为 0%，平均工具调用较 memory off 降低 43.72%，中位耗时降低 58.67%。

- 权限与安全：实现 allow/deny 规则、危险命令确认、dontAsk/plan/acceptEdits 等权限模式和 permission trace；在 24 个覆盖敏感读取、越权修改、危险 shell 与正常操作的真实 Agent 任务中，18/18 风险操作被阻止，危险操作拦截率 100%，正常操作误拦截率 0%，违规修改为 0。

- 工具可靠性与失败闭环：通过任务级 trace 定位 Windows 默认编码导致的非 UTF-8 文件写入问题，统一 `read_file/write_file/edit_file` 的 UTF-8 行为，使同一 20 任务集成功率由 95% 提升至 100%，平均工具调用由 6.20 降至 5.65，平均运行时间由 13.412 秒降至 12.329 秒；进一步识别并修复过度具体断言、弱测试和初始失败 fixture 三类 benchmark 缺陷，并保留原始 run 与复测 provenance。

说明：以上四模块专项数字来自 2026-07-18 的 DeepSeek 真实 API 单轮评测；原始结果、任务级 trace、diff、validator 和校正 provenance 均保存在 `evals/results`。
