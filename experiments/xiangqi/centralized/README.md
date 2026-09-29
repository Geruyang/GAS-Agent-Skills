# 静观棋室

原生 HTML/CSS/JavaScript ES modules 中文象棋，本地双人，无依赖或外部素材。打开共享本地预览 `http://127.0.0.1:8765/centralized/`（若服务器根目录为 experiments/xiangqi），或从仓库根目录提供 HTTP 服务后访问 `/experiments/xiangqi/centralized/`。ES modules 需 HTTP 服务，不能直接双击 HTML。

红先行。点击己方棋子，再点击圆点或圆环标记的落点。方框代表选中；上一步保留端点标记。支持键盘 Tab、方向键、回车/空格和 Esc。悔棋撤回一手并恢复行棋方，翻转只改变视角，重新开始清空棋谱并红先行。

引擎 `engine.js` 不依赖 DOM，固定黑上红下坐标。导出 createInitialBoard、isInCheck、getLegalMoves、applyMove、getGameStatus。合法移动创建完全独立的棋盘；非法输入返回原棋盘且不修改。实现全部基本走法、将军、自陷将军过滤、将帅照面、将死与困毙判负。客户端终局停止走棋，可悔棋恢复。

不提供长将/长捉裁定、联网、AI、竞赛计时、音效或存档。棋谱使用固定 A–I 列 / 1–10 行的坐标记法，翻转后保持稳定。

测试（仓库根目录 PowerShell）：

```powershell
$env:XIANGQI_MODE='centralized'
node --test experiments/xiangqi/tests/acceptance.test.mjs experiments/xiangqi/centralized/rules.test.mjs
```

作者：`/root/v2_central_commander/executor`。本轮 run：`xiangqi-v2-centralized`；产品契约 v1。浏览器独立验收由审查者执行，执行者自测不替代独立验收。
