# 三种治理模式开发的象棋客户端

这是用户明确要求的第二轮实验：主会话只启动实验并比较结果，三个团队由独立 Agent 按集权（4席）、分权（3席）、组合（6席）架构开发。团队身份见 [ROLES.md](ROLES.md)，重启与边界见 [EXPERIMENT.md](EXPERIMENT.md)。

## 运行与试玩

需要 Node.js，无需安装 npm 依赖。在本目录运行：

```powershell
node serve.mjs
```

浏览器打开 <http://127.0.0.1:8765/>，分别进入三个棋室。服务只监听本机；如果显示端口已占用，先打开上述地址检查已有本次服务，不要重复启动。

- 集权版：<http://127.0.0.1:8765/centralized/>
- 分权版：<http://127.0.0.1:8765/decentralized/>
- 组合版：<http://127.0.0.1:8765/combined/>

红先行，本地双人。选择己方棋子后选择落点；可悔棋、翻转棋盘和重新开始。三个实现都按同一 [产品契约](CONTRACT.md) 开发。本示例不含 AI、联网、比赛长将长捉裁定。

## 复核结果

```powershell
node --test tests/acceptance.test.mjs
node measure.mjs
```

第一条运行每组相同的30项规则测试；第二条由外部观察者重跑共测并记录代码规模及逐文件摘要到项目 `.gas/experiments/xiangqi-v2/external/`。外部测量不修改组内产品，也不代替组内治理决定。

三组自行出具的原始运行记录位于项目 `.gas/runs/xiangqi-v2-centralized/`、`xiangqi-v2-decentralized/`、`xiangqi-v2-combined/`。用户停止的第一轮材料已移至 `output/xiangqi-aborted-20260929-01/`，不计入本轮结果。

## 阅读比较

最终实测说明见 [COMPARISON.md](COMPARISON.md)。这是一次同模型、同功能、每组一个产品作者的示范；并发调度影响墙钟时间，无法精确归属的 token 与费用为未知，不作普遍因果排名。

## 公开包与本地证据

仓库公开实验源码、测试、比较报告与截图；`.gas/` 中的历史 Agent 运行记录和 `output/` 中的中止轮次归档未随仓库发布。`node measure.mjs` 会产生你本次复测的记录；随后可运行 `node verify-evidence.mjs` 核对文件是否仍匹配该次测量。复测不能重建或证明原实验的全部角色协作轨迹。
