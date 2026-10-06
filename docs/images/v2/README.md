# GAS 2.0 架构图

三种模式沿用旧版双栏布局、浅灰底与蓝色角色卡片，内容按 2.0 协议更新。中文和英文各提供三张 3600×2760 PNG，以及可缩放 SVG。仓库首页使用 PNG；上级目录旧图片继续作为历史资料。

可编辑绘图源：[render_architecture.py](../../render_architecture.py)。需要 Python、Pillow 和中文字体；生成工具不是技能运行依赖。在仓库根目录执行：

```powershell
python docs/render_architecture.py
```

默认使用 Windows 微软雅黑；其他系统可通过 `--font` 与 `--bold-font` 指定中文字体。SVG 查看端需提供 Microsoft YaHei 或 Noto Sans CJK SC；PNG 已固定字形。
