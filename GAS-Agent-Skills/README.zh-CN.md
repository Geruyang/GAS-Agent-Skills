# GAS 三模式技能包

[返回项目首页与三张框架图](../README.md)

本包按 **集权 → 分权 → 组合** 提供三种多 Agent 开发模式，共享真实授权、独立证据和精确版本验证的要求。

| 模式 | 入口 | 核心职责 |
| --- | --- | --- |
| 集权 v3 | [gas-centralized-development](gas-centralized-development/SKILL.md) | 指挥者统一派工，执行、审查、监督分别取证，指挥者负责集成发布 |
| 分权 v2 | [gas-decentralized-development](gas-decentralized-development/SKILL.md) | 立规者、执行者、裁衡者三方平级，规则与实现均受独立审查 |
| 组合 | [gas-combined-development](gas-combined-development/SKILL.md) | 外层分权，外层执行者兼任内层集权指挥者，两层验收后统一交付 |

集权与分权可以分别复制、分别使用；组合技能依赖同级的集权与分权技能。需要结合时显式使用组合协议，不要将两种独立模式同时作为同一次运行的最高调度权威。

## 创建子 Agent 前的客户端交互

三个技能均要求按 AGENT-01 执行：先在客户端弹窗中让人类选择模型、推理强度和速度，再弹窗展示每个 agent 的职责、路径、交付物和边界，允许人类修改；最终职责得到明确接受后才创建。新增、替补以及组合模式的内外层均适用。未答复、预选和超时不算同意。

选项来自当前宿主实际能力。无法单独设置速度时，必须说明并让人类选择接受当前速度或暂缓创建；没有原生弹窗工具时暂缓创建，不假装已经询问。本包提供流程规则，不修改客户端程序，也不增加模型接口不支持的参数。

## 读取与加载

在实际开发项目的聊天中，提供对应 `SKILL.md` 的绝对路径，请 Agent 同时读取其关联协议，再给出任务、允许修改范围、验收标准与预算。组合模式还需读取同级集权、分权入口与协议。

使用宿主的技能发现机制时，将完整技能目录放入该宿主支持的目录，并确认已经识别。普通目录中的文件不会自动注册为技能。详细组合示例见 [架构与使用说明](gas-combined-development/references/architecture-guide.md)；其中作者本机路径需替换为你的路径。

每个技能包含 `SKILL.md`、`references/`、`templates/` 和 `evals/`。复制时保留整个目录；仅复制入口会丢失协议和记录模板。

## PowerShell 复制安装

从此包目录执行，推荐显式提供目标绝对路径：

```powershell
powershell -NoProfile -File .\Install-GAS-Skills.ps1 -Destination 'D:\AgentSkills' -WhatIf
powershell -NoProfile -File .\Install-GAS-Skills.ps1 -Destination 'D:\AgentSkills'
```

脚本复制 **三个** 技能目录，先检查来源、SHA-256 清单及全部目标名称，再校验暂存副本并放入目标位置。任意同名目录已存在就停止，不覆盖。它不调用网络、不修改执行策略、不要求管理员权限，也不修改 IDE 配置。为兼容原脚本，省略 `-Destination` 时默认目标仍为 `E:\AIProject\GAS`；公开使用建议总是显式填写目标。

三个目录的安装不是跨目录原子事务；中途失败可能留下本次已安装的目录，错误会报告这些路径并保留它们。来源、目标及目标祖先不得是符号链接或目录联接。来源应为干净的完整包，额外缓存文件会触发清单检查；运行 Python 校验时使用 `-B` 避免新增缓存。

如果系统执行策略阻止脚本，可以手动复制三个完整技能目录，无需更改执行策略。SHA-256 用于检测文件缺失或意外损坏，不是发布者签名。

## 记录与能力边界

模板保留 `example_only=true` 和未执行、未批准状态。运行前依据真实项目填写路径、身份、版本、预算与证据；实际记录建议保存到目标项目 `.gas/runs/<run-id>/`，不要将运行状态写回模板。

完整分权需要三个独立身份，完整组合默认需要六个独立身份（均含主会话）。没有真实子 Agent 或独立审查者时，按对应技能说明报告能力不足与等待项，不用同一会话切换角色名称冒充独立团队。

本包不附带模型运行器、原子任务队列、预算服务、强制沙箱或发布服务。既有适用授权可以复用；技术通过、管理接受、集成与发布分别记录。

## 离线校验

Python 3.9+，仅使用标准库。在此包目录执行：

```powershell
python -B .\verify_bundle.py
python -B -m unittest discover -s tests -v
python -B .\gas-centralized-development\scripts\validate_skill.py
python -B -m unittest discover -s .\gas-centralized-development\tests -v
```

包检查包含集权与分权的结构、模板和规则检查，以及整个包（含组合目录）的文件完整性与 SHA-256。组合协议没有专用的行为验证器。场景均保留 `NOT_RUN`；静态检查不证明模型行为或协作性能。

本次结果见 [VALIDATION.md](VALIDATION.md)。历史审计备份保留在作者本地，仓库只收录 [历史验证说明](../docs/history/validation-20260928.md)。修改内容后应重新核验并有意更新交付清单，不能仅为掩盖检查失败而更新散列。
