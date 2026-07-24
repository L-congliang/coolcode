# CoolCode 四模块专项评测报告

## 1. 结论摘要

本报告记录 2026-07-18 使用真实 DeepSeek API 完成的四模块任务级评测。模型配置为 OpenAI-compatible provider 与 `deepseek-v4-pro`，评测对象为 Python Agent Runtime。

| 模块 | 任务规模 | 核心结果 |
| --- | ---: | --- |
| 权限与安全 | 24 tasks | 风险操作拦截率 100%，正常操作误拦截率 0%，违规修改 0 |
| 上下文压缩 | 12 episodes × off/on | 两侧成功率均 100%，累计 prompt token 降低 40.87% |
| 记忆模块 | 12 episodes × off/on | memory on 12/12，off 0/12，命中率与正确应用率均 100% |
| 工具调用效率 | 30 repo-level tasks | 校正后 30/30，通过率 100%，平均 6.833 tools、5.867 turns |

四项正式 run 的 Harness 估算成本合计约 6.18 美元。该估算使用项目内置成本模型，实际费用应以 DeepSeek 控制台为准。

本轮为 R1 单轮正式实验，并对发现的 benchmark 缺陷做了定向复测；尚未完成规划中的 3 次重复，因此不能把本报告解读为置信区间结果。

## 2. 评测方法

- 所有代码任务复制到独立临时 workspace。
- 真实 Agent 负责读取、搜索、编辑、执行 shell 和运行测试。
- Harness 保存工具 trace、permission decision、compression event、memory event、diff、validator 与 token。
- 对照实验固定模型、prompt、fixture 和 validator，只切换 compression 或 memory。
- 安全任务只包含假的 secret 和 canary；危险命令在权限层被拒绝，不进入宿主机 shell。
- prompt token 口径为 `input + cache_read + cache_creation`。

## 3. 权限与安全

### 3.1 任务集

| 类别 | 数量 | 预期行为 |
| --- | ---: | --- |
| 敏感文件读取 | 6 | 拒绝读取假的 `.env` |
| 受保护文件修改 | 6 | 拒绝修改 canary |
| 危险 shell | 6 | 拒绝 `rm -rf cache` |
| 正常编辑对照 | 6 | 允许编辑并通过 unittest |

### 3.2 结果

- 任务通过率：24/24，100%。
- 风险操作：18/18 被正确阻止，拦截率 100%。
- 正常操作：6/6 被允许并完成，误拦截率 0%。
- 敏感文件实际读取：0。
- 受保护文件违规修改：0。
- 平均工具执行数：1.583。
- 平均运行时间：8.015 秒。
- Harness 估算成本：0.4197 美元。

风险任务中的模型调用会出现在 `permission_decision`，但被拒绝的工具不会进入真实执行，因此 tool count 为 0 是预期行为。

正式 run：
`results/2026-07-18_19-28-09_deepseek_safety_24_r1`

## 4. 上下文压缩

### 4.1 任务集

12 个长上下文 episode，每个包含 3 个连续 prompt：

1. 读取约 180 行架构背景并记住 ACTIVE RULE。
2. 读取长诊断日志和当前实现。
3. 在保留早期规则的前提下修改代码并运行 unittest。

每个 episode 分别运行 `compression_off` 和 `compression_on`，共 24 个真实任务。评测使用 7,000 token 的受控有效窗口，使合成长上下文可以稳定触发压缩。

### 4.2 结果

| 指标 | Compression Off | Compression On | 变化 |
| --- | ---: | ---: | ---: |
| 成功率 | 12/12，100% | 12/12，100% | 0 pp |
| 累计 prompt token | 1,622,449 | 959,334 | -40.87% |
| 平均工具调用 | 8.333 | 10.167 | +22.01% |
| 平均 turns | 7.250 | 7.583 | +4.59% |
| 平均运行时间 | 27.419 秒 | 39.126 秒 | +42.70% |
| Harness 估算成本 | 1.4858 美元 | 1.7348 美元 | +16.76% |

其他结果：

- Compression on 共记录 64 次压缩事件。
- 从会话历史中累计移除 720,621 字符。
- 12/12 任务在压缩后仍保留 ACTIVE RULE，信息保持率 100%。
- On 侧出现 23 次重复读取，off 侧为 0，说明压缩降低 token 的同时增加了信息恢复成本。

结论：当前压缩机制显著减少累计上下文 token，并保持任务成功率，但增加工具调用、重复读取、耗时和估算成本。下一步优化重点应是降低过度压缩与压缩后的重复读取。

正式 run：
`results/2026-07-18_19-33-40_deepseek_context_12_pairs_r1`

## 5. 记忆模块

### 5.1 任务集

12 个 memory episode，每个包含两个 follow-up。两个 follow-up 使用全新的 Agent 实例，因此不能依赖会话历史，只能依赖隔离 memory store。

- `memory_off`：memory store 为空。
- `memory_on`：写入合成项目约定。
- Episode 10-12 同时包含 obsolete 和 current 记忆，用于检查 stale-memory pollution。

总计 24 个 variant task、48 个独立 Agent 上下文。

### 5.2 结果

| 指标 | Memory Off | Memory On | 变化 |
| --- | ---: | ---: | ---: |
| Episode 成功率 | 0/12，0% | 12/12，100% | +100 pp |
| 有 retrieval 的任务 | 0/12 | 12/12 | +100 pp |
| 平均工具调用 | 13.917 | 7.833 | -43.72% |
| 平均 turns | 9.333 | 5.000 | -46.43% |
| 中位运行时间 | 46.310 秒 | 19.142 秒 | -58.67% |
| 累计 prompt token | 829,723 | 426,033 | -48.65% |
| Harness 估算成本 | 1.0802 美元 | 0.4656 美元 | -56.90% |

其他结果：

- Memory on 共记录 40 次 retrieval event。
- 检索命中率：12/12，100%。
- 正确应用率：12/12，100%。
- 冲突 episode：3/3 使用 current 记忆。
- Stale-memory pollution：0/3，0%。

Memory off 的失败是对照组预期结果：Agent 无法知道隐藏项目约定，因而不应猜测并修改文件。一个 off 任务出现 814.718 秒 API 长尾，因此耗时对比使用中位数作为主要指标。

正式 run：
`results/2026-07-18_19-49-10_deepseek_memory_12_pairs_r1`

## 6. 工具调用效率

### 6.1 任务集

30 个 repo-level 代码任务：

- 9 个 bugfix。
- 3 个 test-writing。
- 3 个 refactor。
- 3 个多文件 context。
- 2 个 safety-aware coding。
- 10 个精确编辑与测试任务。

### 6.2 校正后结果

| 指标 | 结果 |
| --- | ---: |
| 任务通过率 | 30/30，100% |
| Validator 通过率 | 100% |
| 平均工具调用 | 6.833 |
| 中位工具调用 | 7 |
| 平均 turns | 5.867 |
| 中位 turns | 6 |
| 平均运行时间 | 18.141 秒 |
| 中位运行时间 | 18.252 秒 |
| 平均 prompt token | 35,255.8 |
| 失败工具调用 | 19，总计 0.633/任务 |
| 重复读取 | 0 |
| Harness 估算成本 | 0.9932 美元 |

此前同一 20 任务基线中，UTF-8 工具写入缺陷导致成功率 95%；修复 `write_file/edit_file` 编码后提升至 100%，平均工具调用 6.20 降至 5.65，平均运行时间 13.412 秒降至 12.329 秒。

### 6.3 Benchmark 缺陷闭环

30 任务首轮为 26/30。失败分析发现 4 个失败中有 3 类 benchmark 问题：

1. Test-writing 任务使用了提示中未规定的具体号码字符串，测试实际已经通过。
2. 两个新增计算任务只有一个输入断言，常量实现也能通过 validator。
3. Refactor fixture 在 Agent 运行前已经失败：源码输出字面量 `\\n`，测试要求真实换行。

修复标准：

- 删除过度具体且与行为无关的字符串断言。
- 为计算任务增加第二个输入，阻止常量投机实现。
- 修复 refactor 原始 fixture，并验证 Agent 前测试、dry-run oracle 和真实复测。

校正结果集没有覆盖原始 run，而是通过 overlay 生成，并在 `provenance.json` 中记录 5 次替换来源。

原始 run：
`results/2026-07-18_20-16-03_deepseek_tool_efficiency_30_r1`

校正结果：
`results/2026-07-18_20-48-00_deepseek_tool_efficiency_30_corrected`

## 7. 工程产出

- Python task schema 支持 suite、variant、episode、多 prompt、memory store 和 compression 开关。
- Trace 新增 permission、compression、memory、tool error 与 run config 事件。
- Metrics 新增安全混淆矩阵、完整 prompt token、memory retrieval、失败工具调用和重复读取。
- 每个 run 生成 `manifest.json`、`summary.json/md`、`tasks.jsonl`、任务级 diff、trace 和 validators。
- 新增 run consolidation，能够保留原始结果并记录 benchmark 修正 provenance。
- 新增 82 个专项 task 文件及对应 deterministic fixture。
- Python 测试：17 tests 通过，5 skipped。

## 8. 局限性

- 当前是单轮 R1，模型输出存在随机性；正式论文式结论需要 3 次重复。
- 上下文实验使用 7,000 token 受控窗口，结果代表压力测试，不等同于模型原生最大窗口。
- 费用为 Harness 估算，不是 DeepSeek 账单值。
- Memory off/on 的主要目标是测检索与应用，memory 写入本身由确定性 fixture setup 完成。
- 校正后的 30/30 包含定向复测，原始 26/30 和修正 provenance 均被保留。

## 9. 可用于简历的量化表述

推荐直接使用 `FOUR_MODULE_RESUME.md` 中的版本。面试时应能解释任务设计、控制变量、validator、trace、benchmark 缺陷和单轮实验限制。
