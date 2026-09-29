# 对弈 · 分权实验版

原生 HTML/CSS/JavaScript 本地双人象棋，无网络依赖。用实验共享服务打开 `http://127.0.0.1:8765/decentralized/`；ES modules 需要 HTTP 服务，不直接双击 HTML。

红方先行。点选本方棋子，圆点为合法空位、虚线方框为可吃敌子；选中棋子为双重描边。方向键可在棋盘移动焦点，Enter/空格选子与落子。棋谱坐标是固定棋盘“列,行”，左上为1,1，翻转只改变视角。

支持全部七类棋子规则、马腿象眼、炮架、九宫和过河限制、将帅照面与自陷将军过滤；将死、困毙、缺将判负，终局停止移动。悔棋撤回一手（含吃子和终局），重新开始重置对局但保留视角。

不包含AI、联网、计时、存档及比赛长将/长捉裁定。

测试（从 experiments/xiangqi 目录，PowerShell）：

```powershell
$env:XIANGQI_MODE='decentralized'
node --test tests/acceptance.test.mjs decentralized/rules.test.mjs
```

engine.js 是无 DOM 的纯规则模块，接口按共同 CONTRACT.md。app.js 管理轮次、不可变棋盘历史、棋谱与视角。UI 用本机中文字体、SVG棋盘线和原生按钮，不加载外部素材。

作者为分权执行席。治理及版本证据在 `.gas/runs/xiangqi-v2-decentralized/`；该目录是实验记录，玩家界面不承担治理流程。
