# 🍅 专注 — 桌面番茄钟

一个简洁的 Windows 桌面计时器，帮助你专注学习。

## 功能

- **自定义时长** — 滚轮选择 00~24 小时、00~59 分钟
- **科目标签** — 预设数学、英语、编程等，可自定义
- **环形进度** — 倒计时可视化，hh:mm:ss 显示
- **历史记录** — 按日/周/月查看专注统计，环形图展示科目占比
- **窗口自适应** — 自由拉伸，界面自动适配

## 使用

双击 `dist/Pomodoro.exe` 即可运行，无需安装 Python。

或命令行运行：

```bash
python pomodoro.py
```

## 打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name Pomodoro pomodoro.py
```
