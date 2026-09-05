# 弈界（Chess Confluence）： Demo 0.0.1版本

这是一款融合中国象棋与国际象棋的棋类游戏，支持单人对战简易 AI 和本地双人模式。双方使用相同的 40 点资金购买并秘密部署混合棋子；率先吃掉对方将/帅的一方获胜。



## 运行环境

- Python 3.10 或更高版本
- Pygame 2.5 或更高版本



## 安装与启动

### 创建虚拟环境

```bash
conda create -n chess_confluence_env python=3.11
conda activate chess_confluence_env
python -m pip install -r requirements.txt
```



### 使用命令启动

打开终端或命令提示符，进入本文件夹后运行：

```bash
conda activate chess_confluence_env
cd Chess_Confluence
python main.py
```



## 操作说明

### 秘密部署

1. 红方先购买和部署，黑方看不到红方阵容。
2. 点击右侧棋子商品，再点击棋盘上己方四行部署区的交叉点。
   选中商品后，侧栏会用文字和小棋盘展示该棋子的走法与特殊吃子规则。
3. 每方可免费使用中国象棋将/帅，或额外支付3点切换为国际象棋王。将/帅只能部署在己方3×3九宫内；国际象棋王可以部署在己方四行部署区内。
4. 右键点击已经放置的付费棋子，可以撤回并获得全额退款。
5. 单人模式中，确认红方阵容后，AI 会在不知道红方位置的情况下自动部署黑方。
6. 本地双人模式中，点击“确认阵容并交接”后把电脑交给另一名玩家；黑方完成部署后，双方阵容同时公开。

### 正式对局

1. 红方先行，双方轮流移动一枚棋子。
2. 点击己方棋子后，绿色圆点表示可移动位置，红色圆圈表示可以吃子。
3. 本Demo不判定将军或将死，直接吃掉对方将/帅即可获胜。
4. 国际象棋兵到达对方底线后，可以升变为后、车、象或马。
5. 按 `ESC` 可返回主菜单。

### 界面语言

主菜单可在中文、English 和 Français 之间切换。所选语言会应用于菜单、部署说明、对局状态和弹窗，并在重新开局时保留。



## 当前棋子价格

| 棋种 | 棋子 | 价格 |
|---|---|---:|
| 中国象棋 | 兵/卒 | 1 |
| 中国象棋 | 仕/士 | 1.5 |
| 中国象棋 | 相/象 | 2 |
| 中国象棋 | 马 | 2.5 |
| 中国象棋 | 炮 | 4.5 |
| 中国象棋 | 车 | 6 |
| 国际象棋 | 兵 | 1 |
| 国际象棋 | 马 | 3 |
| 国际象棋 | 象 | 3.5 |
| 国际象棋 | 车 | 6 |
| 国际象棋 | 后 | 10 |

每方最多购买20枚棋子；每种棋子的购买上限沿用其原棋种的标准数量。



## 第一版规则核心内容

### 汇总

- 不判定将军、将死、飞将。
- 允许走入受攻击位置；胜负仍以实际吃掉将/帅为准。
- 当前行动方没有任何合法走法时判负，该规则同时适用于单人和双人模式。
- 同一局面第三次出现，或连续 100 个半回合没有吃子及兵/卒移动时，判为和棋。
- 内置可调难度电脑 AI，并支持 JSON 存档、撤销与回放；暂不支持联网和音效。

### 国际象棋

- 排除国际象棋的困毙。
- 排除国际象棋的王车易位和吃过路兵。
- 保留国际象棋的升变。
- 保留国际象棋兵首次移动可以前进两格。

### 中国象棋

- 排除中国象棋的将帅照面。
- 排除象和士的活动范围限制。
- 保留将/帅仍只能在九宫内移动一步。

## Single-player AI

The main menu supports either a single-player game against the built-in AI or
the original local two-player mode. In single-player mode, the player can choose
Red or Black, Easy/Medium/Hard difficulty, deterministic or varied AI setup,
and whether the initial armies may be inspected after the match. The game-over
screen supports rematches with the same armies or a newly generated AI army.

AI implementations use the renderer-independent `GamePolicy` protocol in
`ai.py`. A future reinforcement-learning adapter only needs to implement:

```python
class MyRLPolicy:
    def choose_setup(self, request: SetupRequest) -> SetupPlan: ...

    def choose_move(
        self,
        observation: GameObservation,
        legal_actions: tuple[MoveAction, ...],
    ) -> MoveAction | None: ...

    def choose_promotion(
        self,
        observation: GameObservation,
        pawn: PieceView,
        options: tuple[str, ...],
    ) -> str: ...
```

`GameObservation` and all actions are immutable and contain no Pygame objects.
The game supplies an explicit legal-action mask and validates policy setup and
move outputs before changing live state. Inject a replacement with
`HybridChessGame(ai_policy=MyRLPolicy())`.

## Development guide

The code is split by responsibility:

- `main.py`: Pygame screens, input, rendering, and AI-turn scheduling.
- `engine.py`: authoritative match state, setup validation, actions, and results.
- `pieces.py`: board model and movement rules, with no Pygame dependency.
- `ai.py`: AI contract, snapshots/actions, and the built-in heuristic policy.
- `match_history.py`: JSON records plus validated replay and undo support.
- `settings.py`: board constants, integer half-point prices, limits, colors, and
  assets. One internal cost unit equals 0.5 displayed points.
- `i18n.py`: Chinese, English, and French message catalogs.
- `tests/`: rule, localization, and AI regression tests.

See [docs/RULES.md](docs/RULES.md) for exact variant and terminal rules. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for state flow, invariants,
extension instructions, and an RL-policy adapter example.
[docs/MATCH_RECORDS.md](docs/MATCH_RECORDS.md) documents the JSON format,
save/load API, and replay validation.

GitHub Actions runs linting, formatting, type checking, tests, and a headless
application import on Python 3.10 and 3.13 for every push and pull request.

Run the automated checks from the project root:

```bash
python -m pip install pytest ruff mypy
python -m pytest -q -p no:cacheprovider
ruff check --no-cache main.py engine.py match_history.py ai.py pieces.py settings.py i18n.py tests
ruff format --check --no-cache main.py engine.py match_history.py ai.py pieces.py settings.py i18n.py tests
python -m mypy main.py engine.py match_history.py ai.py pieces.py settings.py i18n.py tests \
  --ignore-missing-imports --cache-dir=NUL --no-error-summary
```
