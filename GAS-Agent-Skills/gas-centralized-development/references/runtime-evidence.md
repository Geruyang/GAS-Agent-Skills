# 运行证据与候选核验

[运行证据模板](../templates/runtime.example.json) 是独立的 schema 1 附表；[核验工具](../scripts/gas_runtime.py) 只读取文件和记录。它不执行记录里的命令，不启动 agent，不复制或冻结目录，也不实施交付。原模式的契约、指令／申领、审查、监督、裁衡及交付记录继续生效。研究来源与实验解释见 [研究借鉴与评价边界](research-basis.md)。

## 三个命令

在本技能目录运行，或把脚本替换为其实际路径。`CANDIDATE_DIR`、`MANIFEST_JSON`、`RUNTIME_JSON` 均替换为真实路径；命令行相对路径按当前工作目录解释。

```powershell
python -B scripts/gas_runtime.py manifest --candidate CANDIDATE_DIR --output MANIFEST_JSON
python -B scripts/gas_runtime.py verify --candidate CANDIDATE_DIR --manifest MANIFEST_JSON
python -B scripts/gas_runtime.py assess --candidate CANDIDATE_DIR --manifest MANIFEST_JSON --record RUNTIME_JSON
```

| 命令 | 实际作用 |
| --- | --- |
| `manifest` | 扫描整个候选目录，生成文件路径、长度、SHA-256 和目录清单，返回 `candidate_digest`。输出必须在候选目录外，父目录须已存在。已有输出字节完全相同时可复用；不同内容拒绝覆盖。 |
| `verify` | 重新扫描 `--candidate`，与候选外的清单逐项比较，列出新增、缺失、变化文件及目录差异。候选路径必须显式提供，不从清单加载任意根目录。 |
| `assess` | 先执行候选比对，再核验运行附表的必要字段、候选摘要、证据引用及已实现的状态约束，返回 `technical_evidence_ready` 和 `issues`。 |

正常执行输出 JSON。退出码 `0` 表示该命令条件满足；`1` 表示候选不同或运行证据条件未满足；`2` 表示参数、主输入读取、非法清单或其他输入错误使工具无法完成。个别证据文件缺陷会进入 `issues` 并返回 `1`。参数错误可能输出命令行用法；不能把“进程运行完毕”当作核验通过。

## 冻结候选与清单

先在受控目录准备完整候选，再停止写入并生成清单。清单、运行附表、日志和后续报告放在候选之外。工具没有忽略规则：隐藏文件、缓存等只要位于候选中都会参与核验；包括空目录在内的全部目录也参与摘要。根目录绝对路径不参与摘要，因此迁移或复制后可复核，但必须保留全部文件、相对路径和目录，且不能混入额外文件。

清单按排序后的规范 JSON 计算 SHA-256；文件条目仅含 `path`、`size`、`sha256`。重复 JSON 键、非标准数值、额外清单字段、不合法哈希或大小、大小写重名及缺失／冲突父目录均被拒绝。相对路径用 `/`，不得含空段、`.`、`..`、反斜杠、盘符或 ADS 冒号、尾点／空格、控制字符、Windows 保留设备名等。工具拒绝 Windows 扩展／设备路径，以及候选、清单、证据路径及祖先上的符号链接和 reparse point／junction。

冻结后有改动就形成新候选，记录影响并按原协议补验，不能只替换旧证据中的摘要。审查前和发布前重新 `verify`。`assess` 结束前还会读回候选、清单、运行记录和证据，以发现检查过程中的变化。读取前后的状态检查只能发现部分并发变化，不能证明可抵抗恶意并发文件替换；运行时必须使用冻结、受控的候选目录。

## 运行附表怎样填写

从模板另存实际运行记录，保留示例文件的 `example_only=true` 和未执行状态。实际记录只有在填写真实事实时才使用 `example_only=false`。`binding` 必须含 `run_id`、`task_id`、`command_or_claim_id`、`recipient`、`epoch`、`contract_version`、`candidate_digest`、`idempotency_key`；其中 `epoch` 为非负整数或非空字符串，其余为非空字符串。候选摘要须与清单一致。原权威记录通过 `governance_record_refs` 引用并由原治理流程核对，CLI 不认证引用的授权或身份。

`binding.epoch` 和 `binding.candidate_digest` 是附表索引，不重命名原字段：集权继续使用 `coordinator_epoch`、`plan_version`、`artifact_digest`；分权继续使用各席 `governance.roles.<role>.epoch`、任务 `owner_epoch`、交付 `actor_epoch` 和 `artifact_digest`；组合继续使用两层角色任期、桥接契约／计划版本、`candidate_digest` 和 `delivery.shared_epoch`。附表不能把外层平级角色纳入内层指挥，也不新增治理席位。

证据统一登记在 `evidence` 数组，每项含唯一 `id`、`path`、`sha256`、`input_digest`。`path` **相对运行附表所在目录**，不是候选目录或当前工作目录；只能向下引用，不能用 `..` 逃逸。工具读取非空普通文件，核对字节 SHA-256 和相应输入摘要：普通产品检查、回执及适用性证据绑定当前候选；复用的预检原始证据保留源输入摘要，规则见下一节。`checks[].evidence_refs`、回执等字段引用的是这些证据的 **ID**，不是路径或嵌套对象。文件存在且哈希吻合只说明所读文件一致，不证明日志或签名真实。

`checks` 至少有一项 `required=true`。检查 ID 不可重复，每项 `input_digest` 都绑定当前候选，并分开记录：

| 字段 | 可用值与含义 |
| --- | --- |
| `execution` | `NOT_RUN`、`RUNNING`、`COMPLETED`，表示执行观察。 |
| `result` | `UNKNOWN`、`PASS`、`FAIL`、`INCONCLUSIVE`，表示事实结论。 |

未完成检查只能填 `UNKNOWN`；完成的检查必须引用有效证据。必选检查须为 `COMPLETED` 且 `PASS` 才满足本工具条件。已运行但证据不足应保留 `COMPLETED`／`INCONCLUSIVE`，不能改为未执行或通过。可选检查的未执行或有证据支撑的 FAIL 不单独阻止 `technical_evidence_ready`，原治理的真实阻塞条件仍然有效。工具不从原契约自动推导完整必选项，检查范围和结论仍由原模式审查。

## 验证归属与独立分析

每项独立开发任务由一个具名执行者同时负责实现和针对该任务的验证，包括测试／验证代码、执行命令、原始输出与失败处理。集成或跨模块检查也须由指挥者指定具名执行者；分权模式由平级执行者按契约确认归属。审查者／裁衡者接收执行者输出及可用监督／监控输出，对照精确候选、需求、覆盖、异常与证据有效性分析问题，给出补证要求和判断；不编写或修改测试／验证代码，不代做实现。发现证据不足时把补证交回具名执行者；审查者可以对读原始记录、进行静态分析及复跑已有获准命令，保持独立判断，不能把执行者自测直接当作独立接受。

`verification_ownership` 记录 `executor_identity`、`task_ref`、`test_code_paths`、`execution_evidence_refs`、`analysis_owner_identity` 和 `supplement_request_refs`。身份、任务和候选与原模式记录相互绑定；尚未分工或未执行时保留 null／空列表。`review_method.independent_method` 表示独立分析方法，可引用既有检查复跑、需求与日志交叉核对、边界推理；确定性计算证据中的新增程序仍由执行者编写。独立性取决于真实身份、分析过程和适用证据，不要求审查者编写另一套测试。

这些新增归属字段由原治理流程核对；本 CLI 不认证作者身份，也不强制验证全部新增字段。新职责不改变精确候选、硬失败、独立审查或裁衡门禁。

## 并行任务与监控记录

执行者数量 N 为正整数，默认 1，用户可以指定。原运行契约 `execution_team` 登记数量来源、真实执行者名单与任务分工；`assignments` 每项应绑定任务、具名执行者、开发路径、测试／验证路径、依赖、共享资源及证据交付对象。`role_hosting` 默认 minimum 与角色类型不限制 N；实际确认名单与就绪屏障必须覆盖全部 N 名执行者。集权需要 N+3 个真实子 agent，分权 N+2，组合内层 N 名执行者时 N+5；每种再加一个主会话，组合桥接双职只算一个身份。

集权及组合的指挥者在全员 TEAM_READY 后主动拆分工作，尽可能让依赖满足、路径及资源不冲突的任务同时运行。实现、各自验证、已有产物审查及监督监控可以重叠；依赖未满足的动作保留等待，已就绪的独立任务无需等待另一任务验收。分权各平级执行者按有效契约协调认领与资源，不新增指挥席。共享写入、同一板卡烧录／调试、危险设备操作等须登记资源占用范围与释放证据，只串行受冲突影响的动作；独占资源不可因不同工作副本而假定独立。指挥者记录未并行原因，不通过绕过授权、全员屏障、预算或真实宿主并发上限增加任务数。

集权和组合监督者持续对照指挥者意图监督全部执行者与审查者，监测板卡电压、电流、运行状态、agent 工作状态及软硬件异常；向指挥者报告，原始监督输出同时供审查分析。每项监测登记数据来源、单位、采样时刻与间隔、阈值及依据、观测值、异常影响、上报对象和处置状态。采样记录同时注明 `sampled_at`、`evaluated_at`、`freshness_rule_ref` 与有效窗口／新鲜度结果；有效性依据未知或采样过期记 `INCONCLUSIVE`／不可用，保留历史值但不能用作当前正常值。单一遥测通道缺测或过期是监测覆盖缺口，监督者仍能独立履行其他职责时仅阻塞受影响硬件动作；监督角色身份、通信或整体履职能力缺失才按原协议关闭全员屏障。不可测、采样过期或阈值未知须明确标记，不能写成正常或已安全；必需安全监测缺失时报告并请求暂停受影响动作，实际暂停／断电等只按既有明确授权。监控工具或采集代码缺失时交具名执行者补齐，监督者不自行改变产品代码、测试或安全阈值。分权不增加监督席：各执行者记录自己的运行与安全观测并共享，裁衡者分析异常与证据缺口。

## 关键能力预检

涉及业务产物的小样本预检只在原协议要求的全员 `TEAM_READY` 并统一启动后进行；组合模式覆盖内外两层。按原协议核对已有授权、限定试验范围和预算，可引用有版本的试验许可或草案标准；不能要求待预检支持的正式契约先已生效。`team_ready_evidence_ref` 保留对应来源，准备完成须由原协议核对；当前脚本不验证该字段或全员就绪，不能仅凭自填字段声称已就绪。真实关键能力按适用标准列为 `required=true`，不能把它改成可选项绕过预检。

`critical_capability_preflight` 使用相同执行／结论结构。其 `input_digest` 记录实际被测的源输入；原始 `evidence_refs` 绑定该源摘要。源摘要与当前候选不同而仍需复用时，增加 `applicability`，填写 `source_input_digest`、`target_candidate_digest`、`environment`、`coverage`、`reviewer`、`reason` 和 `evidence_refs`。其中源／目标摘要须分别匹配预检输入和当前候选，适用性证据绑定当前候选。原治理流程核对环境、覆盖范围及复用理由；不能修改历史证据摘要来伪装新检查。普通产品 `checks` 仍精确绑定当前候选。

对于记录为 `COMPLETED`／`PASS` 的预检，`actual_output_ref` 指向真实输出证据 ID，且包含在该项 `evidence_refs` 中。用 `output_assertion` 记录预先确定的断言：`{ "kind": "utf8_exact", "expected": "预期文本" }` 比较实际文件完整字节与非空文本的 UTF-8 编码，换行、空白和 BOM 差异均影响结果；`{ "kind": "sha256", "expected": "预期的64位小写摘要" }` 只比较实际输出文件的 SHA-256。仅在省略 `output_assertion` 时，才兼容读取旧 `expected_output` 作为文本断言；空对象或 `null` 不触发兼容回退。不能把刚读出的实际内容或哈希复制成期望值来冒充预检。

其他格式或内容检查可由确定性工具输出可观察摘要，再按上述方式核对；或保留原模式要求的完整解析、视觉、公式等检查记录。二进制哈希相符只证明字节相符，实际功能仍须原契约要求的功能证据。小样本只支持已测范围，不替代完整验收；本工具不具备通用内容真伪、视觉质量或语义正确性判断。

若预检列表为空，必须同时填写 `preflight_applicability.status="NOT_APPLICABLE"`、非空 `reason` 和 `contract_ref`，说明契约依据。空列表不等于预检通过；真实适用性与既有预检复用范围仍需原治理核对。

## 生命周期、恢复与依赖

`lifecycle` 分别保留 `sent`、`received`、`started`、`completed`。每阶段可为 `NOT_RUN` 或 `COMPLETED`；未观察、未知或没有可靠回执时保留 `NOT_RUN` 并说明限制，不能据此断言外部动作从未发生。已完成阶段须按顺序出现，引用有效 `host_receipt_ref`，且事件 `binding` 与顶层完全一致。成功发送不等于目标已接收，检查通过不等于真实任务已启动；全部生命周期仍为 `NOT_RUN` 不会单独阻止技术证据条件满足。

`checkpoint.side_effect_status` 区分 `NONE`、`UNKNOWN`、`CONFIRMED_NOT_APPLIED`、`CONFIRMED_APPLIED`，`retry_requested` 使用 JSON 布尔值。请求重试时，未知副作用先查明，已有副作用不重做；只有 `NONE` 或有完成核对及证据支撑的 `CONFIRMED_NOT_APPLIED` 能满足工具的重试条件。继续执行还须核对原授权、当前门禁和剩余预算；工具既不查询外部系统，也不自动重试或提供强制幂等服务。

`stage_dependencies` 使用唯一字符串 `nodes` 与 `{ "from": "前驱", "to": "后继" }` 的 `edges`。工具拒绝缺失端点、重复边、自环和有向环，仅检查 DAG 结构，不调度任务、不证明依赖产物已生成，也不自动调整治理顺序。

## 解释结果与实验

`technical_evidence_ready=true` 只表示本工具已实现的机械一致性条件满足，不是授权、调度 ready、团队就绪、独立审查、管理接受或裁衡结论，也不是发布许可。`risk_acceptance`、`human_adjudication` 与 `delivery` 分开保留；接受风险、人类决定及原治理裁决不能改写技术 FAIL。交付执行与结果也分开记录，已完成交付须引用证据；工具不认证其外部效果或授权。

`task_structure`、`progress`、`review_method`、`metrics` 等字段提供记录建议；除脚本明确实现的字段检查外，它们不是完整强制校验，更不是调度器。`mode`、`record_type`、治理记录引用及风险／人类决定也不经过实质认证；不以填写这些字段作为有效治理证据。未知调用次数、token、费用、耗时和误通过情况保留 `null`，不填成零。工具无法证明签名真实性、实际身份与权限、隔离能力或预算强制执行。

在 `GAS-Agent-Skills` 包根运行工具故障实验：

```powershell
python tests/run_runtime_experiments.py --output NEW_DIRECTORY
```

`NEW_DIRECTORY` 必须尚不存在。实际输入、输出和结果保存在该新目录；永久场景模板 `evals/runtime-scenarios.json` 保持 `NOT_RUN`。这类实测检验文件篡改、证据缺口、状态和依赖等工具故障边界，不比较三种治理团队的性能，不能用工具耗时或场景数量推断团队效率。

## 角色承载与进展展示

原运行契约的 `main_session` 登记主会话身份与展示用途；`role_hosting` 登记治理角色必须由真实子 agent 承担。主会话不计入角色人数，也不承担业务执行或治理决定。完整默认配置为集权 4 个、分权 3 个、组合 6 个治理子 agent；组合外层执行者与内层指挥者对应同一个子 agent。总会话数另加主会话，所有交互与转接成本仍计入同一预算。

实际 `roster` 每行记录 `roles`、`agent_identity`、`host_session_kind`（必须为 `subagent`）、`parent_identity`、`creation_receipt_ref`、`role_confirmation_ref` 与 `readiness_receipt_ref`。按真实宿主回执核对身份、子 agent 关系、角色覆盖、独立性及主会话身份排除；组合桥接两项职责在同一行登记。不得因字段自填、消息发送成功或空名单就设 `verified=true` 或 TEAM_READY。缺席时等待补齐，主会话不接任；模板检查和本 CLI 都不能认证宿主关系或自动建立这个屏障。

主会话展示具名角色的进展、产物引用、原始检查结论、阻塞及待人类决定事项。人类交互及宿主必要的创建／消息转接遵循已确认名单、具名角色的原始指令或用户直接指令，保留来源和回执；转述不形成主会话自己的批准、裁决或派工权，也不授权它代做实现、测试或交付。
