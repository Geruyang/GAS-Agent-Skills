# 分权开发模式技能 v2

固定三个平级 agent：立规者 legislator、执行者 executor、裁衡者 arbiter。入口及机器标识仍为 gas-decentralized-development。编写结构参考指挥者模式，治理关系独立；三个身份不能由一个会话假扮。

## 从旧版迁移

旧版按模块设置多个执行者，新版按三种权力设三个固定席位。主会话默认任立规者，再建两个子 agent；单执行席自主选择就绪任务并承担获准集成发布。登记服务不再占 agent 席位，也不取得管理裁决权。

五份模板为运行、任务、评审、异议、交付；schema_version 为 2。运行记录新增 governance 与 contract，默认 single-executor-self-claim。旧 coordinator 字段移除；runtime.reviewer_identity 是 arbiter 身份的兼容镜像，实际运行须一致。旧 lease/fencing 字段仅在真实后端支持时使用。所有示例均未批准、未执行。

旧记录不能直接标成 v2 生效：重新核对三方真实身份、任期、当前契约、授权和评审对象，保留旧记录供追溯。已有有效证据可核对后复用，不凭迁移重置预算。

## 人类意图与规则复议补充

裁衡者同时审查规则与实现，规则需符合有来源的人类意图；执行者可直接请立规者复议规则，无需先证明裁决错误；立规者可建议人类调整意图，但仅在明确同意范围内更新，不同意或未答复时不得改动。

运行模板新增 human_intent 与 contract.intent_review；异议模板新增 route、rule_reconsideration 和 intent_change。旧 v2 记录补齐真实意图来源和待执行审查状态后再用，不能把缺失字段补成已批准。人类拒绝不影响旧意图效力，人类同意也不改写旧测试事实。详见协议 SEP-06 至 SEP-08。

## 阶段性规则复盘

按协议 SEP-09，在阶段或最终交付节点简短复盘规则效果与成本。执行者提供执行事实，裁衡者评估保障与风险，立规者汇总保留、简化、修改或废止建议。复用交付记录；建议不自动改规，后续修改沿用既有审查与人类意图变更流程，不因普通优化建议阻塞已获验交付。

## 使用

读取 [SKILL.md](SKILL.md) 和 [协议](references/protocol.md)，按真实项目启动三个角色。人类不占 agent 席位，缺一席不自动兼任；分权开发模式技能是协作约定，不附带调度器或强制权限服务。

## 验证

在包根运行 `python -B verify_bundle.py --skill gas-decentralized-development`，运行 `python -B -m unittest discover -s tests -p test_separation_contract.py -v` 检查反例。模板和校验器不承担运行时授权。

32 个 [压力场景](evals/scenarios.json) 均保留 NOT_RUN。静态通过、文字决策探针和真实多 agent 工具执行须分别报告；未实测性能、硬隔离或生产发布。此次检查证据保存在项目外层 update-audit/separation-v2-20260928，不纳入可复制技能的运行依赖。
