# 象棋客户端：三种开发模式实际比较

> 公开版本说明：本报告描述原实验时的状态；源码与截图随仓库发布。下文 `.gas/`、`output/` 及指向这些目录的本机证据链接属于作者本地记录，未随仓库公开。读者可以重新运行公开测试，但不能仅凭本仓库独立复核全部历史协作轨迹。

2026-09-29，第二轮。三个技能已安装，三个独立客户端均完成各自治理流程及本地交付。共同规则测试每组30/30，总计90/90；正式审查均首轮通过，正式产品返工均为0。

主会话 `/root` 只启动实验、维护共同测试设施、做外部观察与比较；不占任何组内角色，不实现或修复三组产品，不代行组内接受、裁衡或交付。13个组内 Agent 由全新上下文启动：集权4席、分权3席、组合6席。实际身份见 [ROLES.md](ROLES.md)。

直接打开 [图文对比](http://127.0.0.1:8765/comparison.html)，可切换桌面/390px截图并进入各版本试玩：

- [集权 · 静观棋室](http://127.0.0.1:8765/centralized/)
- [分权 · 对弈](http://127.0.0.1:8765/decentralized/)
- [组合 · 一局象棋](http://127.0.0.1:8765/combined/)

## 实测结果

| 比较项 | 集权 | 分权 | 组合 |
|---|---|---|---|
| 真实组内角色 | 4 | 3 | 6 |
| 产品作者 | 1 | 1 | 1 |
| 外部共同规则测试 | 30/30 | 30/30 | 30/30 |
| 独立规则/状态检查 | 43/43 | 47/47 | 内层40/40；外层38/38 |
| 浏览器证据 | 审查者独立Edge实操22断言 | 裁衡者独立Edge实操19断言 | 桥接席Edge实操；两层审查核对原始操作、结果和截图 |
| 外部390px宽度测量 | 390px，无页面横向溢出 | 390px，无页面横向溢出 | 390px，无页面横向溢出 |
| 正式候选审查 | 1轮 | 1轮 | 1轮，含内外两层 |
| 首审阻塞 | 0 | 0 | 0 |
| 正式产品返工 | 0轮 | 0轮 | 0轮 |
| 起点至本地交付 | **25分06秒** | **19分27秒** | **34分12秒** |
| 客户端四份源码总字节 | 21,296 | 20,254 | 22,877 |
| 治理状态 | 独立技术PASS + 监督COMPLETE + 指挥者ACCEPT | 独立裁衡VERIFIED | INNER_ACCEPTED + OUTER_VERIFIED |
| 实际交付 | 本地交付及字节一致快照 | 本地交付 | 同一次本地交接供两层引用 |
| Git合并/外部发布 | 未执行 | 未执行 | 未执行 |
| 精确逐组token/费用 | 未知 | 未知 | 未知 |

独立检查数包含共同30项和各组不同的补充测试，不能用数量直接给质量评分。组合的40与38包含重复共同测试，不能相加成78个不同用例。源码字节仅计算 `index.html`、`styles.css`、`app.js`、`engine.js`，不含测试和README；源码行数受压缩与换行风格影响，不用于排名。

“正式产品返工0”不代表从未遇到失败。测试先行的初始失败、CLI调用语法错误、浏览器路径问题、冻结前样式/图标调整等保留在各组记录，未伪装成全程零失败，也没有算成正式裁决退回的产品返工。

## 时间口径

均采用各组实际观测起点至其自身本地交付回执时间，以下为北京时间UTC+8，秒数四舍五入：

| 组 | 观测起点 | 本地交付 | 秒数 |
|---|---|---|---|
| 集权 | 19:42:47 | 20:07:53.286 | 1506.286 |
| 分权 | 19:43:12 | 20:02:39 | 1167 |
| 组合 | 19:44:15 | 20:18:27.457 | 2052.457 |

集权组原始结果另记录到总结封账的26.221分钟；它包含交付后的整理时间，本文没有把它与另组的“到交付”时间混用。各组创建到第一次时钟记录之间的差额未精确测量；三组并发共享工具和计算资源，计时不能用于因果效率排名。

## 客户端实际效果

三组都实现了同一套核心：9×10棋盘、32子开局、红先、本地双人轮流、合法落点、吃子、非法反馈、将军/将死/困毙、终局停棋、悔棋、重开、翻转和棋谱。覆盖马腿、象眼与河界、九宫、炮架、过河兵卒、将帅照面和自陷将军过滤。

外部观察者在三版均用真实控件执行同一个场景：左侧红兵前进一步，观察黑方行棋与悔棋可用，再悔棋恢复红方和原兵位置。三版均符合预期。另逐一目视桌面与窄屏截图，并测量390px时页面宽度均为390px。组内还完成重开、翻转、非法操作、键盘等更完整流程。

- **集权版**：棋谱按红黑两列排列，选中/落点/上一步图例常显；重开操作更醒目。
- **分权版**：显示当前剩余棋子数，悔棋/翻转按钮附短说明；桌面棋盘较紧凑。
- **组合版**：桌面棋盘相对更大，键盘说明常显，棋谱按“手”计数；内层另有4项UI状态VM测试。

这些是当前版本的可观察设计差异，不能归因于治理模式必然产生某种视觉风格。三组共享相同中式棋室brief，未故意使用不同美术标准制造差异。

## 这次实验能支持的判断

本次分权组使用最少席位，最早完成本地交付，同时满足了相同核心验收。集权组真实运行了技术审查、下属监督、指挥者接受的链条。组合组增加外层独立裁衡，并留下两层原始证据，流程时间最长。

**本次共同测试没有拉开功能通过率差距，也没有量化证据证明组合模式的额外流程提高了最终产品质量。** 同样，没有证据证明多一层检查没有价值：本轮没有人为注入缺陷、规则偏离、身份失联或权限冲突，无法评估这些场景下的恢复和制衡能力。

这是小型、同模型、每组一个实现者的单次示范，不体现多个产品作者并行开发大型项目的能力。角色隔离是流程上的真实不同身份，工作区和权限仍共享；不同Agent不代表统计独立。不能据此宣布某种模式普遍最好、最省token或最便宜。

## 安装与重启

三个完整技能安装于 `C:/Users/ruyangge/.codex/skills/`，分别为 `gas-centralized-development`、`gas-decentralized-development`、`gas-combined-development`。逐文件复核：16、9、7个文件，共32个，与项目来源SHA-256全部一致。来源技能未修改。

按用户纠正，第一轮10名子Agent已停止，旧客户端、运行状态和日志归档至 `output/xiangqi-aborted-20260929-01/`，不参与本轮比较。新团队使用 `fork_turns=none`；只保留共同需求和外部测试作为实验输入，不复用旧实现/裁决。宿主不提供抹除聊天历史或模型内部缓存的接口，所以未声称物理清除内部缓存。

用户明确要求主会话不占席，覆盖了技能默认“主会话任一席”的宿主配置；各模式的组内职责分离仍保留。详情见 [EXPERIMENT.md](EXPERIMENT.md)。

## 验证边界和原始证据

未做实体手机或跨浏览器兼容矩阵，未在浏览器自然走完整盘至将死。终局由规则测试、UI代码审阅覆盖，组合另有精确app状态harness；这不等于完整实盘证明。不包含联网、AI、计时比赛、长将/长捉裁定。

- 集权：[最终结果](E:/AIProject/GAS/.gas/runs/xiangqi-v2-centralized/result.json)、[独立审查](E:/AIProject/GAS/.gas/runs/xiangqi-v2-centralized/reviewer/review-001.json)、[监督](E:/AIProject/GAS/.gas/runs/xiangqi-v2-centralized/supervisor/report-003-final.json)、[交付回执](E:/AIProject/GAS/.gas/runs/xiangqi-v2-centralized/delivery-receipt.json)。
- 分权：[最终结果](E:/AIProject/GAS/.gas/runs/xiangqi-v2-decentralized/result.json)、[独立裁衡](E:/AIProject/GAS/.gas/runs/xiangqi-v2-decentralized/arbiter/round-1/verdict.json)、[交付](E:/AIProject/GAS/.gas/runs/xiangqi-v2-decentralized/executor/delivery.json)、[三方复盘](E:/AIProject/GAS/.gas/runs/xiangqi-v2-decentralized/legislator/retrospective.md)。
- 组合：[内审](E:/AIProject/GAS/.gas/runs/xiangqi-v2-combined/inner/reviewer/review-001.json)、[监督](E:/AIProject/GAS/.gas/runs/xiangqi-v2-combined/inner/supervisor/supervision-003-final.json)、[外层裁衡](E:/AIProject/GAS/.gas/runs/xiangqi-v2-combined/outer/arbiter/review-001.json)、[同一次交付回执](E:/AIProject/GAS/.gas/runs/xiangqi-v2-combined/bridge/local-delivery-receipt-001.json)。
- 外部：[30项×3测试及逐文件摘要](E:/AIProject/GAS/.gas/experiments/xiangqi-v2/external/measurement.json)、[证据仍绑定当前文件](E:/AIProject/GAS/.gas/experiments/xiangqi-v2/external/final-evidence-binding.json)、[统一浏览器场景](E:/AIProject/GAS/.gas/experiments/xiangqi-v2/external/browser-observations.json)。
- [共同产品契约](CONTRACT.md)、[30项外部测试源码](tests/acceptance.test.mjs)、[启动与复测说明](README.md)。

测试结果、监督事实、管理决定、独立裁衡和本地交付分别记录，没有把测试通过写成远端发布成功。
