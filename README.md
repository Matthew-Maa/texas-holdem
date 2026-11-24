# 德州扑克（Texas Hold'em）

Python + pygame 写的无限注德州扑克，带图形界面、完整牌力评估，和 6 种不同风格的 AI 对手。

## 怎么跑

需要 Python 3.10 以上。

```bash
pip install pygame
python main.py
```

Windows 上也可以双击 `run.bat`。

## 玩法

两种模式：

- **人类参与**：你坐一个位置，其余是 AI
- **观看 AI**：全部由 AI 打，你只在旁边看（适合观察不同风格的区别）

6 种 AI 风格，靠三组参数区分——入池紧度、加注激进度、诈唬频率：

| 风格 | 特征 |
|---|---|
| 岩石（rock） | 极紧，只玩好牌 |
| 鲨鱼（shark） | 紧且凶，会施压 |
| 跟注站（station） | 几乎不加注，只跟 |
| 疯子（maniac） | 松且极度激进，诈唬多 |
| 均衡型（balanced） | 各项居中 |
| 超紧（nit） | 最紧，几乎不诈唬 |

牌力评估覆盖全部 9 种成手牌型（高牌到皇家同花顺），比较时按标准规则处理踢脚。
界面里按 F1 或点"规则"可以打开内置玩家指南（`玩家指南.pdf`）。

## 关于音乐

**仓库没有包含任何音频文件。** 背景音乐需要自己准备——把 4 个 mp3 放进 `music/` 目录，
按 `bgm_1.mp3` ~ `bgm_4.mp3` 命名即可（曲目列表在 `music_manager.py` 的 `TRACKS` 里，可以改）。

缺音乐时游戏正常运行，只是没有背景音乐（`MusicManager.play()` 里有异常兜底）。

## 目录结构

```
texas_holdem/
├── main.py                 入口、界面与事件循环
├── game.py                 牌局流程（下注轮、翻牌、摊牌）
├── player.py               玩家与 6 种 AI 风格的决策
├── cards.py                牌组与洗牌
├── hand_evaluator.py       牌力评估（9 种牌型）
├── gui_renderer.py         牌桌、座位、按钮绘制
├── music_manager.py        背景音乐管理
├── test_engine.py          牌局引擎测试
├── test_smoke.py           冒烟测试
├── make_guide_pdf.py       生成玩家指南 PDF
├── music/                  背景音乐（空，自行放入）
├── 玩家指南.pdf
└── 项目结构与维护指南.md
```

跑测试：

```bash
python test_engine.py
python test_smoke.py
```

## 许可

个人学习作品。代码可供参考学习；如需转载、二次分发或商用，请先联系作者。
