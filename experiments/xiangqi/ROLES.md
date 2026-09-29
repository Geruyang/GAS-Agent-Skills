# 第二轮实际角色

主会话 `/root`：仅实验启动器、外部测量者和比较报告作者，无组内治理席位。

| 组 | 真实 Agent 身份 | 角色 |
|---|---|---|
| 集权 | /root/v2_central_commander | 指挥者 |
| 集权 | /root/v2_central_commander/executor | 执行者 |
| 集权 | /root/v2_central_commander/reviewer | 审查者 |
| 集权 | /root/v2_central_commander/supervisor | 监督者 |
| 分权 | /root/v2_decentral_legislator | 立规者 |
| 分权 | /root/v2_decentral_executor | 执行者 |
| 分权 | /root/v2_decentral_arbiter | 裁衡者 |
| 组合 | /root/v2_combined_bridge/outer_legislator | 外层立规者 |
| 组合 | /root/v2_combined_bridge | 外层执行者＝内层指挥者 |
| 组合 | /root/v2_combined_bridge/outer_arbiter | 外层裁衡者 |
| 组合 | /root/v2_combined_bridge/inner_executor | 内层执行者 |
| 组合 | /root/v2_combined_bridge/inner_reviewer | 内层审查者 |
| 组合 | /root/v2_combined_bridge/inner_supervisor | 内层监督者 |

13个组内身份全部真实创建且 `fork_turns=none`；共用同一模型配置。外层平级不因宿主父子调用结构改变。与主会话一起是14个活动身份。旧轮次角色已停止，身份与结果不计入本轮。

## 安装核验

三个完整目录安装到 `C:/Users/ruyangge/.codex/skills/`，各自使用项目同名目录。独立只读复核结果：集权16文件、分权9文件、组合7文件，所有来源/安装文件 SHA-256 相同，差异为0。下一轮可由宿主技能发现，本轮各团队直接读项目技能与完整协议。

## 复现实验

1. 在 `experiments/xiangqi/` 执行 `node serve.mjs`，浏览器打开 `http://127.0.0.1:8765/`。
2. 执行 `node --test tests/acceptance.test.mjs` 同时检查三份规则引擎；共用需求固定为 `CONTRACT.md`。
3. 外部测量 `node measure.mjs`，结果写 `.gas/experiments/xiangqi-v2/external/`，不会改产品；读三组各自 `.gas/runs/xiangqi-v2-*/` 原始审查与监督证据。
4. 相同外部输入从空产品目录重跑，分别创建4/3/6席的新上下文。比较耗时前注意并发资源干扰，以及组内协作和平台工具准备成本。

仅本地开发/测试/预览；没有远端发布。技能约束以流程自律和真实证据执行，未建立强制权限沙箱或统计独立性。
