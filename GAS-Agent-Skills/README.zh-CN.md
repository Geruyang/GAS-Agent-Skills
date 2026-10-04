# GAS 三模式技能包 · 2.0

[返回项目首页与三张框架图](../README.md) · [2.0 发布说明](../docs/releases/2.0.md)

本包按 **集权 → 分权 → 组合** 提供三种多 Agent 开发模式，共享真实授权、独立证据和精确版本验证的要求。

| 模式 | 入口 | 核心职责 |
| --- | --- | --- |
| 集权 v3 | [gas-centralized-development](gas-centralized-development/SKILL.md) | 指挥者统一派工，执行、审查、监督分别取证，指挥者负责集成发布 |
| 分权 v2 | [gas-decentralized-development](gas-decentralized-development/SKILL.md) | 立规者、执行者、裁衡者三方平级，规则与实现均受独立审查 |
| 组合 | [gas-combined-development](gas-combined-development/SKILL.md) | 外层分权，外层执行者兼任内层集权指挥者，两层验收后统一交付 |

集权与分权可以分别复制、分别使用；组合技能依赖同级的集权与分权技能。需要结合时显式使用组合协议，不要将两种独立模式同时作为同一次运行的最高调度权威。

## 2.0：职责、多执行者与主动并行

每名具名执行者负责独立任务的开发与验证，包括测试／验证代码及原始执行证据。审查者和裁衡者分析执行者及可用监督／监控输出，发现问题并要求补证，不编写测试／验证代码。新增验证工作交给具名执行者；独立判断、精确候选与最终门禁保留。

集权及组合监督者持续核对全部执行者和审查者是否符合指挥者意图，监测板卡电压、电流、运行、agent 工作状态及软硬件异常并汇报。不可测、过期采样或未知阈值明确标注，不冒充正常。分权保留三类平级职责，各执行者记录并共享自己的监控事实，不新增指挥或监督席。

集权及组合指挥者尽可能把已就绪独立任务并行派出；分权执行者在契约内协调并行分工。依赖、冲突写入、共享板卡烧录／调试或资源占用只约束相关动作。已有 AGENT-01 全员就绪与人类确认要求继续适用。运行记录通过 `execution_team` 和任务验证归属登记实际人数、职责与资源；填写字段不等于宿主已强制隔离或监控已完成。

## 所有角色由子 agent 承担（1.5）

三种技能的所有治理角色都由真实子 agent 承担。主会话展示进展、证据引用、等待及需要人类决定的事项，承载已有流程要求的人类交互；不任指挥者、立规者、执行者、审查者、监督者、裁衡者或桥接席，不实施业务、作治理裁决或发布。

执行者数量 N 为正整数，可由用户指定，默认 1。实际集权 N+3、分权 N+2、组合 N+5 个子 agent；默认分别为 4、3、6 个，每种另有 1 个不占角色席位的主会话。组合的外层执行者与内层指挥者仍是同一个子 agent。宿主工具树上的父子关系不授予治理权；必要的创建或消息转接依据已确认名单或具名角色的原始指令，不由主会话决定业务派工与优先级。缺角色或子 agent 能力时保持 `WAITING_FOR_TEAM`，不能由主会话接任来降级继续。

运行模板以 `main_session` 和 `role_hosting` 记录此边界。真实 roster 需核对宿主创建回执、子 agent 身份、角色覆盖及主会话排除关系；模板中的空名单与 `verified=false` 不能当作已经核验。主会话交互、转接和所有层级子 agent 消耗均计入同一运行总预算。

## 运行证据与策略改进（1.5）

三种技能新增同一套标准库证据工具与运行附表：统一记录检查执行和事实结论、关键能力小样本、启动回执、恢复核对、候选摘要、风险处理及交付。各模式继续使用原来的权责与审批记录；新附表通过引用接入，不改变原模板 schema。

- 集权用任务与进展账本识别实际停滞，并在原预算内重规划。
- 分权用结构化验收项减少歧义，执行者保留实施自主权，裁衡者保留独立判断。
- 组合显式记录阶段依赖和原始证据复用，避免两层互等及重复交付。

每个完整技能目录都包含 `scripts/gas_runtime.py`、`references/runtime-evidence.md` 和 `templates/runtime.example.json`。三份工具保持一致，无需导入包根模块。先阅读所用技能的 [运行证据指南](gas-centralized-development/references/runtime-evidence.md)，以已就绪团队的真实记录填写附表；业务能力小样本在 `TEAM_READY` 后开展。

从包目录调用工具，例如对专用候选目录生成清单，再读回校验：

```powershell
python -B .\gas-centralized-development\scripts\gas_runtime.py manifest --candidate C:\Project\.gas\runs\run-1\candidate --output C:\Project\.gas\runs\run-1\candidate-manifest.json
python -B .\gas-centralized-development\scripts\gas_runtime.py verify --candidate C:\Project\.gas\runs\run-1\candidate --manifest C:\Project\.gas\runs\run-1\candidate-manifest.json
python -B .\gas-centralized-development\scripts\gas_runtime.py assess --candidate C:\Project\.gas\runs\run-1\candidate --manifest C:\Project\.gas\runs\run-1\candidate-manifest.json --record C:\Project\.gas\runs\run-1\runtime.json
```

将 `C:\Project` 替换为真实项目；分权、组合可调用各自目录下的同名脚本。清单必须存于候选目录之外。修改候选后建立新的版本与审查证据，不改写原失败。`assess` 的 `technical_evidence_ready` 只是已声明检查的机械一致性结果，不证明证据内容正确，不授予角色权力或发布权限，也不能代替独立审查。风险接受、治理判断和真实交付继续单独记录。

配套实测区分真实文件故障测试、独立文字判定探针和完整治理团队对照。相同工具在三种安装目录通过同输入测试只说明工具行为一致，不构成治理优劣排名；完整治理实验仍须统一任务、外部验收与总预算，成本未知时保留 `null`。机制来源与采用范围见 [研究借鉴说明](gas-centralized-development/references/research-basis.md)。

## 创建子 Agent 前的客户端交互

**默认运行位置（继续保留）：** 所有子 agent 默认通过 Codex 客户端原生通道创建，并在当前任务的子 agent 列表展示。改用 CLI 托管前必须弹窗说明原因并征求同意。用户不同意时，继续排查和尝试列表路径；只有已取得答复、适用列表路线均确实不可行且 CLI 可行时，才按条件性兜底授权执行，并提前在客户端披露证据、角色及查看／停止方式。未回复或明确禁止任何 CLI 时不允许兜底。列表关联／展示证据或合规 CLI 例外纳入全员就绪检查。

所有计划中的子 agent 全部完成创建、确认职责并报告就绪前，主会话与已创建成员都不得推进任务。先创建好的成员仅回复就绪并待命；核齐完整名单后统一通知启动。组合模式覆盖内外两层，新增或替换成员时重新等待，不自动删减缺席角色来提前开工。

三个技能均要求按 AGENT-01 执行：先在客户端弹窗中让人类选择模型和推理强度，再弹窗展示每个 agent 的职责、路径、交付物和边界，允许人类修改；最终职责得到明确接受后才创建。新增、替补以及组合模式的内外层均适用。未答复、预选和超时不算同意。

**V1.4 服务档位规则：** 子 agent 沿用主会话／直接父 agent 的服务档位（速度），不再弹窗选择档位，不单独配置或切换，也不要求档位回执。档位核验不作为创建或全员就绪的门槛；模型、推理强度和职责仍须按原规则确认。

每次弹窗默认预留至少 30 分钟，届满未答复仍延续等待。异步提问返回后使用能被用户消息唤醒的等待工具，以每轮不超过 60 秒的方式保持任务活跃；不推进后续工作、不因未点击发送结束答复、不反复重开弹窗。人类可以延长等待、取消或暂停。

本包提供流程规则，不修改客户端程序，不能设置工具未提供的弹窗保留时长。若宿主强制中断，记录待答状态而非完成，恢复后继续；没有原生弹窗工具时说明能力缺失并暂缓创建，不假装已经询问。

## 读取与加载

在实际开发项目的聊天中，提供对应 `SKILL.md` 的绝对路径，请 Agent 同时读取其关联协议，再给出任务、允许修改范围、验收标准与预算。组合模式还需读取同级集权、分权入口与协议。

使用宿主的技能发现机制时，将完整技能目录放入该宿主支持的目录，并确认已经识别。普通目录中的文件不会自动注册为技能。详细组合示例见 [架构与使用说明](gas-combined-development/references/architecture-guide.md)；其中作者本机路径需替换为你的路径。

每个技能包含 `SKILL.md`、`references/`、`templates/`、`scripts/` 和 `evals/`。复制时保留整个目录；仅复制入口会丢失协议、记录模板和证据工具。

## PowerShell 复制安装

从此包目录执行，推荐显式提供目标绝对路径：

```powershell
powershell -NoProfile -File .\Install-GAS-Skills.ps1 -Destination 'D:\AgentSkills' -WhatIf
powershell -NoProfile -File .\Install-GAS-Skills.ps1 -Destination 'D:\AgentSkills'
```

脚本复制 **三个** 技能目录，先检查来源、SHA-256 清单及全部目标名称，再校验暂存副本并放入目标位置。任意同名目录已存在就停止，不覆盖。它不调用网络、不修改执行策略、不要求管理员权限，也不修改 IDE 配置。省略 `-Destination` 时，默认安装到当前用户目录下的 `.agents/skills`；指定其他位置时继续使用目标绝对路径。默认路径变更适用于本次修订，历史 v1.5 标签中的安装器仍使用旧默认值。

三个目录的安装不是跨目录原子事务；中途失败可能留下本次已安装的目录，错误会报告这些路径并保留它们。来源、目标及目标祖先不得是符号链接或目录联接。来源应为干净的完整包，额外缓存文件会触发清单检查；运行 Python 校验时使用 `-B` 避免新增缓存。

如果系统执行策略阻止脚本，可以手动复制三个完整技能目录，无需更改执行策略。SHA-256 用于检测文件缺失或意外损坏，不是发布者签名。

## 记录与能力边界

模板保留 `example_only=true` 和未执行、未批准状态。运行前依据真实项目填写路径、身份、版本、预算与证据；实际记录建议保存到目标项目 `.gas/runs/<run-id>/`，不要将运行状态写回模板。

完整集权默认需要四个独立子 agent，分权需要三个，组合默认需要六个；主会话均不计入角色身份。没有必需子 Agent 或独立审查者时，按对应技能说明报告能力不足并等待补齐，不用主会话或单一会话切换名称代替缺席角色。

本包不附带模型运行器、原子任务队列、预算服务、强制沙箱或发布服务。既有适用授权可以复用；技术通过、管理接受、集成与发布分别记录。

## 维护资产与版本

运行契约的 schema 按模式分别演进：集权 3、分权 2、组合桥接索引 1；共同 runtime 附表为独立的 schema 1。`mode`／技能路径与 `schema_version` 一起确定记录格式，发行版本 2.0 也不等于 schema 版本。组合行为场景补有自己的 schema 1，不借用集权场景的版本号。

只有集权包含历史专项 `scripts/validate_skill.py`、内部 `tests/` 和协议 `CHANGELOG.md`。分权与组合的专项检查、畸形输入及角色边界回归位于包根 `verify_bundle.py` 和 `tests/`，并非没有校验；三者覆盖范围不同，不声称全部字段或真实治理行为都已验证。跨技能改动统一记在本包验证记录与仓库 `docs/` 中，避免维护三份相互漂移的发行日志。

共同脚本和参考资料在每个技能中保留完整副本，便于分别安装。维护时使用 `scripts/sync_shared_assets.py --check` 检查一致性；确认规范副本改动后才显式 `--write` 同步。AGENT-01 仍位于入口并核对一致性，不隐藏启动规则。

组合技能的 `assets/architecture-codex-guide-v3.png` 与仓库 `docs/images/03-combined.png` 是同源历史图。两份分别服务完整技能复制和历史文档链接，保留旧路径；其中旧主会话任职安排已被现行文字与首页 Mermaid 图替代。

## 离线校验

Python 3.9+，仅使用标准库。在此包目录执行：

```powershell
python -B .\verify_bundle.py
python -B -m unittest discover -s tests -v
python -B .\gas-centralized-development\scripts\validate_skill.py
python -B -m unittest discover -s .\gas-centralized-development\tests -v
python -B .\verify_bundle.py --skill gas-combined-development
python -B .\tests\run_runtime_experiments.py --output C:\Project\gas-runtime-experiment-01
```

包检查包含集权、分权的既有检查及组合独立 schema 的身份、桥接、双层门禁和未执行默认值检查，以及全包文件完整性与 SHA-256。新增运行工具回归使用真实临时文件，覆盖三种技能目录；实验命令的输出目录必须尚不存在，用于保留每次原始结果。组合完整治理仍没有自动行为验证器。场景定义保留 `NOT_RUN`，实际结果另存；静态检查不证明模型行为或协作性能。

本次结果见 [VALIDATION.md](VALIDATION.md)。历史审计备份保留在作者本地，仓库只收录 [历史验证说明](../docs/history/validation-20260928.md)。修改内容后应重新核验并有意更新交付清单，不能仅为掩盖检查失败而更新散列。
