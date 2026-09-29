# 集权开发模式技能 · v3

入口 [SKILL.md](SKILL.md)，规则 [运行协议](references/protocol.md)。技能显示名称为“集权开发模式技能”，指挥者等角色名称及职责保持不变，目录/name保持 `gas-centralized-development`，机器身份字段仍用 `coordinator`。

## 角色与证据

指挥者管理执行者、审查者和监督者，并承担集成发布。监督者只检查执行者、审查者的规则遵守、不安全行为和指令理解偏差，受指挥者调度并向其汇报，不监督指挥者。指挥者唯一的角色监督者是人类；平台权限和真实技术门禁依旧有效。

技术验证、下属监督、管理决定分开留档。监督不能代替技术测试或独立审查。指挥者亲自修改实现时，仍须取得另一真实审查者或人类对精确产物的技术验证；这不把监督者变成指挥者的上级。监督者无默认暂停他人任务权限；有效限定委托下才能最小暂停，恢复、终止、重派仍由指挥者决定。

## 文件

| 文件 | 用途 |
|---|---|
| [运行契约](templates/run.example.json) | 真实授权、监督范围、角色、预算、交付归属 |
| [任务契约](templates/task.example.json) | 实施、验证、监督、决定与交付状态 |
| [统一指令](templates/command.example.json) | 任期、身份、范围、有效期与确认 |
| [验证记录](templates/review.example.json) | 技术事实与独立性 |
| [监督报告](templates/supervision.example.json) | 下属实际行为、规则、安全与理解偏差 |
| [管理决定](templates/decision.example.json) | 指挥者引用验证与监督证据作裁决 |
| [交付记录](templates/release.example.json) | 指挥者自己的集成、部署、回滚及真实回执 |
| [压力场景](evals/scenarios.json) | 48个可复用场景；模板状态保持NOT_RUN |

七份JSON均为 `schema_version=3`、`example_only=true`。未知身份、空证据、未签发指令不构成已建立能力。示例要求接受前具备监督覆盖；实际调整要求须来自有效契约，不能因环境不足就默认为不需要。

## 使用与迁移

明确要求Agent读取本目录SKILL.md，并说明真实项目和目标。存放文件不自动完成宿主发现、注册或激活；Skill不实现运行器、权限隔离、命令队列或生产门禁。

保留v1/v2记录；已有任务先到安全点，核对旧integrator行动、回执、幂等键与外部状态，由当前指挥者接管未完成交付职责，不能自动重发。v2技术验证不是v3监督记录；建立真实监督身份和覆盖。旧授权可在核实仍适用后复用，角色变更不产生额外权限。

此次只修改集权Skill和必要包级配套；分权Skill保持原样。完整包根校验器已支持v3，根散列清单与本次候选对应；旧备份清单保持原样，不把旧清单不匹配当成现包损坏。

## 检查

Python 3.9+，只使用标准库；将 `py -3` 换成本机可用Python命令即可。

```powershell
py -3 .\scripts\validate_skill.py
py -3 -m unittest discover -s tests -v
```

完整包根目录另运行 `py -3 .\verify_bundle.py` 及根 `tests`。校验器检查示例结构、缺省状态、链接和关联，不是实际运行记录的安全执行器。

本次真实子Agent文字决策探针、原文、无Skill对照、变异测试和只读审查记录保存在项目 `update-audit/commander-v3-20260928/`。它们不等于48场景在真实项目中全部执行，也不证明多Agent协作性能、强制权限隔离或生产可靠性。场景模板NOT_RUN不写成PASS；真实运行结果单独存放。详见完整包VALIDATION.md和审计报告。
