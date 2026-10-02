# 研究借鉴与评价边界

本轮按用户确认的三技能改进策略补充可执行记录与核验工具。下列来源是 2026-09-30 下载的固定版本；核对依据为迁移资料中的原文、源码与证据笔记，不代表项目最新维护状态。借鉴机制不改变三种技能的治理权限，也不证明改进后必然更优。

| 来源与固定位置 | 本次采用 | 适用边界 |
| --- | --- | --- |
| [A2A a2a.proto，第 186–207 行](https://github.com/a2aproject/A2A/blob/1ae57a673f729f743b35f2677f3adc302438695a/specification/a2a.proto#L186) | 区分任务生命周期和真实状态回执。 | A2A 的 SUBMITTED 已包含确认；GAS 的发出、接收、开始、完成四阶段是本项目适配，完成状态不等于治理验收。 |
| [LangGraph types.py，第 887–909 行](https://github.com/langchain-ai/langgraph/blob/f5804a5bf583fecc29676335e707c6b9e600c6d5/libs/langgraph/langgraph/types.py#L887) | 明确恢复点、重执行范围及副作用核对。 | 从节点开始重执行意味着外部动作可能重复；先查询未知结果是本项目约束，不声称框架自动保证所有副作用幂等。 |
| [Magentic-One arXiv 2411.04468v1](https://arxiv.org/abs/2411.04468v1)，§4.1、PDF 第 6–7 页；[AutoGen 实现](https://github.com/microsoft/autogen/blob/027ecf0a379bcc1d09956d46d12d44a3ad9cee14/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_magentic_one/_magentic_one_orchestrator.py#L348) | 任务账本、进展账本、停滞计数与有界重规划。 | 实际进展用产物或检查证据支撑，不直接信任模型自评；不照搬论文阈值或清空历史的做法。 |
| [MetaGPT ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6507b115562bb0a305f1958ccc87355a-Abstract-Conference.html)，§3、PDF 第 4 页；[角色源码](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/roles/role.py#L399) | 结构化中间产物、相关消息与证据引用。 | 该源码快照晚于论文；结构化记录不替代独立判断。 |
| [Towards a Science of Scaling Agent Systems，arXiv 2512.08296v3](https://arxiv.org/abs/2512.08296v3)，PDF 第 7 页 | 依据可拆分性、依赖与协调成本记录执行结构。 | 论文比较通信拓扑；GAS 规定谁定规则、谁执行、谁判断。名称相似不等于实验对象相同，不自动改变用户选定的治理模式。 |
| [Why Do Multi-Agent LLM Systems Fail?，NeurIPS 2025 正式版](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html)，PDF 第 2 页；[MAST 固定版本](https://github.com/multi-agent-systems-failure-taxonomy/MAST/tree/a70542e541b2104ef8fcd785778179e173fb8d70) | 用失败类别组织场景、故障注入和原始轨迹记录。 | 分类和测试输入不是执行结果；本次未重跑原论文轨迹或全部历史压力场景。 |
| [AI Agents That Matter，arXiv 2407.01502v1](https://arxiv.org/abs/2407.01502v1)，PDF 第 1–2 页 | 同时报告质量和成本，控制任务、验收与总预算。 | 本地为 arXiv v1，不是 TMLR 最终版；未知费用、token 和忙碌时长保持 null。 |
| [Anthropic 工程文章](https://www.anthropic.com/engineering/multi-agent-research-system)，本地快照 SHA-256 `b1a554a63ed34c95433dc605c283414258241c8299acb67f2cd2bb4bfd794e3d` | 尽早用小样本检查关键能力与方法。 | 原文讨论早期 agent 评估；本项目将其适配为关键路径探测。它是厂商实践，不是独立性能证明；业务预检遵守 TEAM_READY。 |

## 三种证据层级

1. **静态检查与真实文件故障测试**：证明规定输入下的文件清单、摘要、记录校验和依赖图行为。三个安装目录用相同工具与相同输入测试，验证的是工具一致性。
2. **独立代理判定及使用探针**：检验新代理能否找到指南、实际调用工具、正确解读结果。只对记录的样本有效，不等于完整治理运行。
3. **完整治理对照实验**：需真实配置三套团队，统一任务版本、外部及格线、总预算、模型与工具条件，保留所有尝试和失败，按既有协议重复运行。只有这一层可用于讨论协议本身的比较，且仍需说明样本范围。

## 真实运行的共同评价口径

实验前固定 task_id / input_digest、外部验收版本、预算及停止条件；记录用户实际选择的治理模式，并单独记录执行拓扑、角色数、共享状态和依赖。角色结构不同不能被隐藏；未经授权不增减角色或换模式。

每次保留输出质量、是否误通过、漏检项、墙钟耗时、可观测调用次数、人工介入次数，以及 token / 金额 / 忙碌时长的来源或 null。误通过需由独立外部判据认定；未测不能填 false 或 0。明确原始证据读取次数、实际检查重跑次数和逻辑检查项数的计数单位。工具耗时不能冒充团队执行耗时。

本次工具没有实现宿主调度、跨进程原子队列、强制预算或权限隔离；检查点字段、幂等键和事件回执是可核对记录，不是基础设施保证。新工具结果不能覆盖原 FAIL / NOT_RUN，也不能把接受风险、管理接受或裁衡签名写成新的技术通过。
