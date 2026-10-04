# 参与 GAS 的开发与验证

感谢你愿意参与。GAS 尚未在实际工程项目中得到充分验证，真实任务中的成功经验、失败案例和反例都能帮助改进它。无需先获得仓库写入权限，也不要求先贡献代码。

## 从哪里开始

| 你想做什么 | 参与入口 |
| --- | --- |
| 询问用法、讨论角色设计、交流经验 | [Discussions](https://github.com/Geruyang/GAS-Agent-Skills/discussions) |
| 提交实际项目验证结果 | [实际项目验证报告](https://github.com/Geruyang/GAS-Agent-Skills/issues/new?template=validation_report.md) |
| 报告可复现的问题 | [问题反馈](https://github.com/Geruyang/GAS-Agent-Skills/issues/new?template=bug_report.md) |
| 提出具体改进 | [改进建议](https://github.com/Geruyang/GAS-Agent-Skills/issues/new?template=feature_request.md) |
| 修改协议、模板、文档或检查工具 | Fork 本仓库后提交 Pull Request |

模板是辅助记录的工具。信息暂时不全也可以提交，并注明未知项；Issue 创建页保留空白入口。请先搜索已有 Issue 和讨论，相关补充可直接放到现有主题中。

## 怎样提交有价值的验证记录

先选择边界明确、有可核验结果的真实任务，记录以下信息：

1. **环境：** 模型及版本、Agent 宿主、仓库提交版本、所选模式、真实角色数量与工具能力。
2. **目标与边界：** 任务目标、允许修改范围、验收标准、预算与停止条件。
3. **实际过程：** 派工、规则复议、实施、独立审查、返工和最终交付中真正发生的步骤。
4. **结果与成本：** 检查命令和结果、耗时、可获得的调用或 token 数据、失败点及未完成事项。
5. **可选对照：** 在尽量相同的模型、任务、工具和预算下，与不加载技能或其他模式的结果比较，说明不可比因素。

明确区分静态文件检查、文字推演与真实多 Agent 工程运行。缺席角色、未执行的检查和未知能力要如实记录；不要把单个案例推广为普遍性能结论。分享日志前移除密钥、个人信息及无权公开的项目内容，可以提供脱敏的最小复现。

## 提交 Pull Request

1. Fork 仓库，从最新 `main` 建立自己的工作分支。
2. 尽量让每个 PR 解决一个问题，说明触发条件和预期变化。
3. 同步修改受影响的说明、模板或检查；提交实际验证结果及其边界。
4. 向本仓库的 `main` 提交 PR。较大的制度或角色调整，建议先在 Discussion 或 Issue 中说明动机。

首次贡献者的 GitHub Actions 可能需要维护者批准后才能运行，这不影响提交 PR 或参与讨论。维护者会审查贡献并决定合并，不需要申请直接写入权限。

## 本地检查

普通文档修改请检查链接、图片、示例与事实表述。修改技能内容、JSON 模板或校验器时，在仓库根目录执行以下检查；Python 3.9+，只使用标准库：

```bash
python -B GAS-Agent-Skills/verify_bundle.py
python -B GAS-Agent-Skills/scripts/sync_shared_assets.py --check
python -B GAS-Agent-Skills/scripts/update_manifest.py --check
python -B -m unittest discover -s GAS-Agent-Skills/tests -v
python -B GAS-Agent-Skills/gas-centralized-development/scripts/validate_skill.py
python -B -m unittest discover -s GAS-Agent-Skills/gas-centralized-development/tests -v
```

使用 `-B` 避免产生缓存。包级校验覆盖集权、分权的结构与模板，以及含组合目录的全包 SHA-256；它不是组合治理的行为验证器。各模式的评估场景保留未执行模板状态，真实运行结果单独记录。

技能包内的文件变更会影响 `GAS-Agent-Skills/manifest.sha256.json`。确认变更内容后同步更新对应文件的 SHA-256，并再次运行完整包校验；新增或删除文件也要更新清单。不要仅为消除失败而更新哈希。只修改根目录 README、社区文件或许可证时，无需修改技能包清单。

共享资源以 `gas-centralized-development` 为规范来源：`scripts/gas_runtime.py`、`references/runtime-evidence.md`、`references/research-basis.md` 保留三份独立副本。先审查规范来源的修改，再执行同步。工具也检查三份 `SKILL.md` 的 AGENT-01 段落；段落不一致时会在写入资源前停止，须人工核对，工具不会自动改写或移走启动规则。

```bash
git diff HEAD -- GAS-Agent-Skills
python -B GAS-Agent-Skills/scripts/sync_shared_assets.py --write
git diff HEAD -- GAS-Agent-Skills
git status --short -- GAS-Agent-Skills
python -B GAS-Agent-Skills/scripts/update_manifest.py --check
# 核对上述差异以及新增/删除文件，确认每一项均属预期后才更新清单。
python -B GAS-Agent-Skills/scripts/update_manifest.py --write
python -B GAS-Agent-Skills/scripts/update_manifest.py --check
python -B GAS-Agent-Skills/verify_bundle.py
```

两个维护工具省略参数时均为只读检查；`--write` 才写入，`--root` 指定技能包根目录（默认是脚本所在的 `GAS-Agent-Skills`）。清单更新按 POSIX 相对路径排序，排除所有 `manifest.sha256.json` 文件和 `__pycache__`；工具拒绝路径中的符号链接与 Windows reparse point。共享文件逐个原子替换，不提供整批事务；请在无其他进程改写技能包时维护，并完成上述复核。

## 交流与许可

请围绕具体事实和可复现证据讨论，尊重不同结果与不同意见。所有贡献继续保留“实际项目尚未充分验证”的边界，不将未执行的检查记为通过。

项目采用 [MIT 许可证](LICENSE)。提交贡献时，请确认有权提交相关内容，并同意以本项目的 MIT 许可提供；如果涉及第三方内容，请说明来源及许可。再分发本项目或其重要部分时，请保留版权与许可声明。
