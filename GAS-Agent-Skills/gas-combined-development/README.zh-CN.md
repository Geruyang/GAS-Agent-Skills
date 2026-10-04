# 组合模式：验证与迁移说明

本技能连接外层分权与内层集权，提供协议、模板、待运行场景和离线证据工具。内层执行者N>=1，可由用户指定，默认N=1。完整模式需要N+5个真实治理子agent（默认六个），含主会话共N+6个会话；外层执行者与内层指挥者为同一身份、同一任期；主会话另计，只展示进展、承接人类交互和必要机械转接。

每名具名内层执行者独立负责所分模块开发和测试／验证代码及实际验证。内层审查者接收执行者和监督者输出、独立分析问题，外层裁衡者独立分析规则及成果；两者均不编写或修改测试／验证代码，补证由唯一桥接席指派具名内层执行者。已有命令复跑和证据对读可以独立进行。

全层TEAM_READY后，指挥者主动尽可能并行所有独立就绪任务，登记文件冲突、真实共享板卡烧录／调试、依赖与预算约束。监督可与实现和审查并行，持续对照指挥者意图覆盖全部内层执行者和审查者，向指挥者报告板卡电压／电流、运行、agent工作状态及软硬件异常；未知采样／阈值标记不可测。AGENT-01全员屏障保留。每条监测记录采样与评估时刻、freshness_rule_ref及有效窗口；无新鲜度依据或采样过期记INCONCLUSIVE／不可用，不写安全。单一遥测缺口只阻塞依赖该通道的硬件动作及门禁；角色身份、通信或独立履职整体能力缺失才关闭全员屏障，原有暂停授权和真实硬阻塞仍有效。

## 安装与依赖

保留整个技能目录，并将 `gas-centralized-development`、`gas-decentralized-development` 放在同级。启用时依次读取 [入口](SKILL.md)、[组合协议](references/protocol.md) 及入口引用的两个同级协议。缺依赖时先定位同包副本；仍不可读则报告缺口并等待，不凭记忆宣布完整启用。

本技能不附带模型运行器、权限隔离、原子队列或发布服务。worktree 不是安全沙箱。真实角色创建、通信、权限和发布能力取决于宿主，须按协议保留实际回执。

## 模板与版本

| 文件 | 用途与版本 |
| --- | --- |
| [run.example.json](templates/run.example.json) | 组合桥接索引 schema 1，引用两层权威记录；execution_team登记数量来源、具名名单和分工；默认最低人数字段保持六人 |
| [runtime.example.json](templates/runtime.example.json) | 共同运行证据附表 schema 1，登记实际检查、回执、候选和恢复证据，以及verification_ownership、parallel_dispatch、supervision_monitoring |
| [review-reuse.example.json](templates/review-reuse.example.json) | 组合依赖与原始证据复用登记 schema 1，补证请求回桥接并登记具名执行者与验证路径 |
| [scenarios.json](evals/scenarios.json) | 组合行为场景 schema 1，状态永久为 NOT_RUN，执行结果另存 |

版本号属于各自记录族。内层集权运行契约为 schema 3，外层分权为 schema 2，组合索引为 schema 1；它们字段和责任不同，不能因为文件同名就互换。升级实际记录时核对对应模式、版本、角色身份和引用，不批量替换版本号。

## 静态与工具验证

在完整 `GAS-Agent-Skills` 包目录执行（Python 3.9+ 标准库）：

```text
python -B verify_bundle.py --skill gas-combined-development
python -B verify_bundle.py
python -B -m unittest discover -s tests -v
python -B tests/run_runtime_experiments.py --output NEW_DIRECTORY
```

`NEW_DIRECTORY` 必须是尚不存在的结果目录。单技能检查核对入口、依赖链接、模板默认值、桥接及双层门禁、场景结构；完整包检查另核对全部文件与 SHA-256。包根校验器是维护工具，不随三个技能目录单独安装；单独安装后仍可运行本技能的 `scripts/gas_runtime.py`，命令见 [运行证据指南](references/runtime-evidence.md)。

新增分工、数量、资源和监控字段由角色按协议核对，不能声称gas_runtime已自动验证全部登记或实际监控能力。静态检查通过不等于真实N+5身份协作已验证。文件故障实验验证工具面对缺失、篡改及状态错误的行为；文字决策探针只检验场景回应；完整治理运行还需真实角色与通信、独立判断、授权及外部验收证据。`technical_evidence_ready` 不授予验收或发布权限。

模板中的空身份、未批准和 NOT_RUN 不能改作测试成绩。实际运行记录保存到任务项目，保留原始失败及未验证项。
