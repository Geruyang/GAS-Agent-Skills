# 分权开发模式技能 v2

固定三类平级、独立治理职能：立规者 legislator、执行者 executor、裁衡者 arbiter。执行者 N≥1，用户可明确指定，默认 N=1；实际为 1 名立规者、N 名具名执行者、1 名裁衡者，共 N+2 个真实子 agent。入口及机器标识仍为 gas-decentralized-development。编写结构参考指挥者模式，治理关系独立；完整名单身份不能由一个会话假扮。

## 从旧版迁移

按三种权力设三类固定职能，执行者人数可配置，全部由子 agent 担任。主会话不占席，只展示进展、事实和人类输入，并作宿主必要机械转接；默认完整配置为 3 个治理子 agent 加 1 个展示主会话，实际按 N+2 个治理子 agent 计数。每名执行子 agent 协商并自主认领独立模块，负责该项开发、测试/验证代码与实际验证，并按具名归属承担获准集成发布；主会话不能立规、分配业务、实施、裁衡或发布，展示与登记不产生第四治理席。

原五份模板为运行、任务、评审、异议、交付；schema_version 仍为 2，另附独立 schema 的运行证据模板。运行记录新增 governance 与 contract，默认 single-executor-self-claim。execution_team 以 executor_count、count_source、executor_roster、assignments 记录用户指定人数、具名真实身份及任务归属；多执行者使用 peer-executor-self-claim，尽可能并行全部就绪独立任务，共享冲突资源串行。旧 coordinator 字段移除；runtime.reviewer_identity 是 arbiter 身份的兼容镜像，实际运行须一致。旧 lease/fencing 字段仅在真实后端支持时使用。所有示例均未批准、未执行。

旧记录不能直接标成 v2 生效：重新核对 N+2 个独立子 agent 的真实身份、任期、当前契约、授权和评审对象，保留旧记录供追溯；旧的主会话占席记录不能继续作为就绪依据。`governance.main_session_role` 为 null，`agent_count=3`、`budget.max_active_agents=3` 与 `max_active_workers=1` 只表示 N=1 默认治理子 agent 示例，实际按 N+2、N+2、N 登记；主会话通信与转接消耗仍计入全局预算。已有有效证据可核对后复用，不凭迁移重置预算。roles.executor 是默认 N=1 的兼容角色记录，N>1 时不能代表全部执行者；实际以 execution_team.executor_roster 和 role_hosting.roster 核对完整名单。旧 three_distinct_identities_verified 只能证明下限，不能单独证明多执行者全员就绪。缺 execution_team 的旧 schema v2 可按 N=1 解释，新增字段未填写不等于已确认或已创建。

## 开发、验证与安全归属

每名执行者负责一个或多个独立模块的开发与该项验证，包括测试/验证代码和实际执行；task.execution_ownership 绑定具名执行者、开发/验证 owner、路径、共享资源、协商及监控记录。测试标准仍按有效契约，不得为通过降低硬门槛。

裁衡者接收执行者输出和可用监控证据，审查问题、规则忠实性和精确候选成果；不得编写或修改测试/验证代码。缺证据时以 review.evidence_supplement_requests 退具名执行者补齐；可复跑现有命令，保留原始结果并独立判断，不能仅凭执行者的通过签名放行。独立验收、覆盖矩阵和版本证据继续适用。

分权没有指挥者或监督者；每名执行者监控自身执行并上报共享记录，裁衡者分析异常。公共登记单写不产生管理权，独立任务的执行仍尽可能并行；立规者不指挥局部开发，执行者之间互不指挥。新增 verification_ownership 和监控引用供原治理核对；gas_runtime.py 仅核验已有机械证据条件，未宣称已校验新增人数与所有权字段。

## 人类意图与规则复议补充

裁衡者同时审查规则与实现，规则需符合有来源的人类意图；执行者可直接请立规者复议规则，无需先证明裁决错误；立规者可建议人类调整意图，但仅在明确同意范围内更新，不同意或未答复时不得改动。

运行模板新增 human_intent 与 contract.intent_review；异议模板新增 route、rule_reconsideration 和 intent_change。旧 v2 记录补齐真实意图来源和待执行审查状态后再用，不能把缺失字段补成已批准。人类拒绝不影响旧意图效力，人类同意也不改写旧测试事实。详见协议 SEP-06 至 SEP-08。

## 阶段性规则复盘

按协议 SEP-09，在阶段或最终交付节点简短复盘规则效果与成本。执行者提供执行事实，裁衡者评估保障与风险，立规者汇总保留、简化、修改或废止建议。复用交付记录；建议不自动改规，后续修改沿用既有审查与人类意图变更流程，不因普通优化建议阻塞已获验交付。

## 可执行验收与证据附表

`acceptance_criteria` 保留原文，任务模板的 `acceptance_items` 给出逐项结构：意图与条款引用、可观察结果、容差范围、必需性、方法、环境、pass 条件、证据和例外权限。示例的环境、引用与实际命令仍未提供；不能直接视为就绪契约。`intent_coverage_matrix` 连通人类意图、规则、检查与原始证据，裁衡者记录方法独立性，不只记录身份不同。

五份记录以 `runtime_evidence_ref` 接入 [共用附表](templates/runtime.example.json)，语义见 [运行证据规范](references/runtime-evidence.md)。TEAM_READY 后先记录现有授权内的有限试验许可，再做关键路径探测或复用适用证据，最后形成正式生效契约；试验许可不依赖预检先成功，也不授权正式实施或交付。认领、实际开始与提交分开；检查执行状态与事实结论、风险接受、裁衡和实际交付分开。分权仍无管理接受席位，风险接受不能洗掉 FAIL / NOT_RUN / INCONCLUSIVE。

独立复制此技能后可从技能目录运行 `python -B scripts/gas_runtime.py --help`。`manifest --candidate DIR --output FILE` 冻结清单，`verify --candidate DIR --manifest FILE` 核对候选，`assess --candidate DIR --manifest FILE --record FILE` 检查证据；三者都是该脚本子命令，输出文件应放候选之外。工具不调度 agent、不执行发布、不签发裁衡或授权；`technical_evidence_ready` 仅为机械证据条件。

交付新增 `action_id`、`idempotency_key`、`effect_state` 与绑定目标/摘要的 `receipt_probe`。结果未知先查询，在组合模式中两层引用同一行动及回执，只执行一次实际交付。任务依赖与共享写入决定执行结构，不自动变更治理模式。耗时与成本只填真实观测，未知保持 null。

## 使用

读取 [SKILL.md](SKILL.md) 和 [协议](references/protocol.md)，按已确认执行者数量与完整名单创建 N+2 个治理子 agent。人类和主会话均不占治理席位；缺任一子 agent 时保持 WAITING_FOR_TEAM，不由主会话降级实施或他席兼任。AGENT-01 的模型、强度、职责人类选择与 TEAM_READY 全员屏障继续适用；分权开发模式技能是协作约定，不附带调度器或强制权限服务。

## 验证

在包根运行 `python -B verify_bundle.py --skill gas-decentralized-development`，运行 `python -B -m unittest discover -s tests -p test_separation_contract.py -v` 检查反例。模板和校验器不承担运行时授权。

[压力场景](evals/scenarios.json) 均保留 NOT_RUN。静态通过、文字决策探针和真实多 agent 工具执行须分别报告；未实测性能、硬隔离或生产发布。此次检查证据保存在项目外层 update-audit/separation-v2-20260928，不纳入可复制技能的运行依赖。

[运行故障场景](evals/runtime-scenarios.json) 同样保留 NOT_RUN；真实文件实验写入独立运行目录。包检查、证据工具检查、文字判定与真实完整团队运行分别报告，文件故障实验不能证明治理模式孰优。
