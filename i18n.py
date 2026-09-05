"""User-interface translations for Chess Confluence."""

from typing import Literal

Language = Literal["zh", "en", "fr"]

LANGUAGE_LABELS: dict[Language, str] = {
    "zh": "中文",
    "en": "English",
    "fr": "Français",
}

TRANSLATIONS: dict[Language, dict[str, str]] = {
    "zh": {
        "window_title": "融合棋局 · 弈界",
        "menu.title": "融合棋局",
        "menu.subtitle": "中国象棋 × 国际象棋",
        "menu.budget": "点初始资金",
        "menu.rulesets": "套棋子规则",
        "menu.king": "个需要守护的帅",
        "menu.start": "开始本地双人对局",
        "menu.mode.single": "单人 · 简易 AI",
        "menu.mode.local": "本地双人",
        "menu.start.single": "开始单人对局",
        "menu.start.local": "开始本地双人对局",
        "menu.tagline": "双方秘密购买并部署不同棋子，率先吃掉对方将帅者获胜",
        "menu.escape": "ESC 退出",
        "side.red": "红方",
        "side.black": "黑方",
        "game.xiangqi": "中国象棋",
        "game.chess": "国际象棋",
        "piece.xiangqi.bing": "兵/卒",
        "piece.xiangqi.advisor": "仕/士",
        "piece.xiangqi.elephant": "相/象",
        "piece.xiangqi.horse": "马",
        "piece.xiangqi.cannon": "炮",
        "piece.xiangqi.rook": "车",
        "piece.xiangqi.king": "将/帅",
        "piece.chess.pawn": "兵",
        "piece.chess.knight": "马",
        "piece.chess.bishop": "象",
        "piece.chess.rook": "车",
        "piece.chess.queen": "后",
        "piece.chess.king": "王",
        "status.setup.red": "红方请选择棋子并在己方后四行部署。",
        "status.setup.black": "黑方请选择棋子并在己方部署区部署。",
        "status.catalog_selected": "已选择{piece}，点击高亮部署区放置。",
        "status.buy_unavailable": "资金不足，或已达到购买上限。",
        "status.play_start": "红方先行：点击己方棋子查看合法落点。",
        "status.piece_selected": "已选择 {piece}。",
        "status.no_piece": "这里没有本方可操作的棋子。",
        "status.choose_catalog": "请先从右侧商店选择一种棋子。",
        "status.deployment_only": "只能将棋子放在己方部署区内。",
        "status.occupied": "这个位置已经有棋子了。",
        "status.cannot_buy": "当前已无法购买这枚棋子。",
        "status.placed": "已部署{piece}，剩余资金 {budget}。",
        "status.remove_hint": "右键点击己方已购买的棋子可以撤回并退款。",
        "status.king_fixed": "请使用主将选项移动或切换主将。",
        "status.king_selected": "已选择{piece}，请点击合法的起始位置。",
        "status.king_upgrade_unavailable": "切换国际象棋王还需要 3 点资金。",
        "status.king_place_xiangqi": "将/帅必须放在己方九宫内。",
        "status.king_place_chess": "国际象棋王必须放在己方四行部署区内。",
        "status.king_placed": "已放置{piece}。",
        "status.removed": "已撤回{piece}并退还 {cost} 点资金。",
        "status.promote": "国际象棋兵到达底线，请选择升变棋子。",
        "status.turn": "轮到{side}行动。",
        "status.ai_ready": "AI 已完成秘密部署，红方先行。",
        "status.ai_thinking": "AI 正在思考……",
        "status.ai_moved": "AI 将{piece}移动到 ({column}, {row})。轮到红方。",
        "setup.title": "{side}秘密部署",
        "setup.budget": "剩余资金  {budget} / {total}",
        "setup.count": "已购棋子  {count} / {maximum}",
        "setup.instructions": "选中商品后点击高亮交叉点；右键撤回并退款",
        "setup.king_label": "主将",
        "setup.king.xiangqi": "将/帅",
        "setup.king.chess": "国象王 (+3)",
        "setup.shop": "棋子商店",
        "setup.price": "{cost}点   {count}/{limit}",
        "setup.movement": "{piece}走法",
        "setup.preview.move": "可移动",
        "setup.preview.capture": "仅吃子",
        "setup.preview.screen": "炮架",
        "setup.preview.blocker": "阻挡",
        "setup.preview.before_river": "过河前",
        "setup.preview.after_river": "过河后",
        "setup.preview.first_move": "仅首次可走两步",
        "setup.preview.last_row": "到底线后升变",
        "setup.preview.double_only": "圆环：仅首次两步",
        "setup.preview.facing_allowed": "允许照面",
        "setup.finish": "确认阵容并交接",
        "movement.xiangqi.bing": "向前一步；过河后也可横走一步，不能后退。",
        "movement.xiangqi.advisor": "沿对角线走一步；本游戏不限制九宫。",
        "movement.xiangqi.elephant": "沿对角线走两步；象眼被堵时不能走，本游戏可过河。",
        "movement.xiangqi.horse": "走“日”字；马腿被堵时不能走。",
        "movement.xiangqi.cannon": "沿直线任意移动；吃子时必须隔一枚炮架。",
        "movement.xiangqi.rook": "沿横线或竖线任意移动，不能越过棋子。",
        "movement.chess.pawn": (
            "向前一步，仅首次可走两步；斜向前吃子，到达底线后必须升变。"
        ),
        "movement.chess.knight": "走L形（两格加一格），可以跳过棋子。",
        "movement.chess.bishop": "沿对角线任意移动，不能越过棋子。",
        "movement.chess.rook": "沿横线或竖线任意移动，不能越过棋子。",
        "movement.chess.queen": "沿横线、竖线或对角线任意移动，不能越子。",
        "movement.xiangqi.king": (
            "在己方九宫内横走或竖走一步；本版本允许双方将/帅在同一直线上照面。"
        ),
        "movement.chess.king": "向周围任意方向走一步。",
        "play.title": "正式对局",
        "play.turn": "当前回合：{side}",
        "play.checked": "{side}已被将军！",
        "play.rules": "本局规则",
        "play.rule.moves": "• 点击本方棋子，绿色点为移动，红圈为吃子",
        "play.rule.king": "• 不判将军或将死，可直接吃掉对方将帅",
        "play.rule.promotion": "• 国际象棋兵（pawn）到底线后可升变",
        "play.rule.xiangqi": "• 中国象棋棋子保留蹩马腿、炮架等规则",
        "play.status": "状态",
        "play.ai_opponent": "对手：简易 AI",
        "play.escape": "ESC 返回主菜单",
        "handoff.red.title": "红方部署完成",
        "handoff.red.body": "请红方离开屏幕，然后把电脑交给黑方。",
        "handoff.red.button": "我是黑方，开始部署",
        "handoff.play.title": "双方部署完成",
        "handoff.play.body": "阵容将在下一步同时公开，红方首先行动。",
        "handoff.play.button": "公开阵容并开始",
        "handoff.privacy": "此页面不会显示上一位玩家的阵容",
        "promotion.title": "兵已到达底线：选择升变",
        "promotion.queen": "Q 后",
        "promotion.rook": "R 车",
        "promotion.bishop": "B 象",
        "promotion.knight": "N 马",
        "game_over.title": "对局结束",
        "game_over.winner": "{side}获胜！",
        "game_over.draw": "和棋",
        "game_over.reason.king_capture": "成功吃掉了对方的将帅",
        "game_over.reason.no_legal_moves": "对方没有合法行动",
        "game_over.reason.threefold_repetition": "同一局面重复出现三次",
        "game_over.reason.move_limit": "连续 100 个半回合没有吃子或兵的移动",
        "game_over.reason.resignation": "对方认输",
        "game_over.restart": "重新开局",
        "game_over.menu": "返回菜单",
    },
    "en": {
        "window_title": "Chess Confluence",
        "menu.title": "Chess Confluence",
        "menu.subtitle": "Xiangqi × Chess",
        "menu.budget": "starting points",
        "menu.rulesets": "piece rule sets",
        "menu.king": "king to protect",
        "menu.start": "Start local two-player game",
        "menu.mode.single": "Single player · Simple AI",
        "menu.mode.local": "Local two-player",
        "menu.start.single": "Start single-player game",
        "menu.start.local": "Start local two-player game",
        "menu.tagline": (
            "Build secret mixed armies and capture the opposing king to win"
        ),
        "menu.escape": "ESC to quit",
        "side.red": "Red",
        "side.black": "Black",
        "game.xiangqi": "Xiangqi",
        "game.chess": "Chess",
        "piece.xiangqi.bing": "soldier",
        "piece.xiangqi.advisor": "advisor",
        "piece.xiangqi.elephant": "elephant",
        "piece.xiangqi.horse": "horse",
        "piece.xiangqi.cannon": "cannon",
        "piece.xiangqi.rook": "chariot",
        "piece.xiangqi.king": "general",
        "piece.chess.pawn": "pawn",
        "piece.chess.knight": "knight",
        "piece.chess.bishop": "bishop",
        "piece.chess.rook": "rook",
        "piece.chess.queen": "queen",
        "piece.chess.king": "king",
        "status.setup.red": "Red: choose pieces and deploy in your rear four rows.",
        "status.setup.black": "Black: choose pieces and deploy in your zone.",
        "status.catalog_selected": "{piece} selected; click a highlighted point.",
        "status.buy_unavailable": "Insufficient funds or purchase limit reached.",
        "status.play_start": "Red moves first. Select a piece to see its moves.",
        "status.piece_selected": "Selected {piece}.",
        "status.no_piece": "No movable piece of yours is there.",
        "status.choose_catalog": "Choose a piece from the shop first.",
        "status.deployment_only": "Pieces must be placed in your deployment zone.",
        "status.occupied": "That position is already occupied.",
        "status.cannot_buy": "You can no longer buy this piece.",
        "status.placed": "Placed {piece}. {budget} points remain.",
        "status.remove_hint": "Right-click one of your purchased pieces for a refund.",
        "status.king_fixed": "Use the Leader options to move or switch your king.",
        "status.king_selected": "{piece} selected; choose an allowed starting point.",
        "status.king_upgrade_unavailable": (
            "The chess king upgrade needs 3 more points."
        ),
        "status.king_place_xiangqi": (
            "The general must be placed inside your 3×3 palace."
        ),
        "status.king_place_chess": (
            "The chess king must be placed within your four-row deployment zone."
        ),
        "status.king_placed": "Placed {piece}.",
        "status.removed": "Removed {piece}; refunded {cost} points.",
        "status.promote": "Your pawn reached the last row. Choose a promotion.",
        "status.turn": "{side} to move.",
        "status.ai_ready": "The AI has secretly deployed. Red moves first.",
        "status.ai_thinking": "The AI is thinking…",
        "status.ai_moved": ("AI moved {piece} to ({column}, {row}). Red to move."),
        "setup.title": "{side} — secret setup",
        "setup.budget": "Budget  {budget} / {total}",
        "setup.count": "Pieces  {count} / {maximum}",
        "setup.instructions": "Select, then place; right-click to refund",
        "setup.king_label": "Leader",
        "setup.king.xiangqi": "Xiangqi general",
        "setup.king.chess": "Chess king (+3)",
        "setup.shop": "Piece shop",
        "setup.price": "{cost} pts   {count}/{limit}",
        "setup.movement": "How {piece} moves",
        "setup.preview.move": "move",
        "setup.preview.capture": "capture only",
        "setup.preview.screen": "screen",
        "setup.preview.blocker": "blocker",
        "setup.preview.before_river": "Before river",
        "setup.preview.after_river": "After river",
        "setup.preview.first_move": "Two steps on first move only",
        "setup.preview.last_row": "Promotes on last row",
        "setup.preview.double_only": "ring = first-move double",
        "setup.preview.facing_allowed": "Facing is allowed",
        "setup.finish": "Confirm army and hand over",
        "movement.xiangqi.bing": (
            "Moves one step forward; after crossing the river, it can also move "
            "sideways. It never retreats."
        ),
        "movement.xiangqi.advisor": (
            "Moves one step diagonally. In this game, it is not confined to the palace."
        ),
        "movement.xiangqi.elephant": (
            "Moves two steps diagonally and cannot jump a blocked eye. It may cross "
            "the river in this game."
        ),
        "movement.xiangqi.horse": (
            "Moves one step straight, then one diagonally. A blocked horse-leg "
            "stops it."
        ),
        "movement.xiangqi.cannon": (
            "Slides along ranks and files. To capture, it must jump exactly one screen."
        ),
        "movement.xiangqi.rook": (
            "Slides any distance along ranks and files, but cannot jump pieces."
        ),
        "movement.chess.pawn": (
            "Moves one step, or two only on its first move; captures diagonally and "
            "must promote on the last row."
        ),
        "movement.chess.knight": "Jumps in an L shape: two squares, then one.",
        "movement.chess.bishop": (
            "Slides any distance diagonally, but cannot jump pieces."
        ),
        "movement.chess.rook": (
            "Slides any distance along ranks and files, but cannot jump pieces."
        ),
        "movement.chess.queen": (
            "Slides any distance along ranks, files, or diagonals; it cannot jump "
            "pieces."
        ),
        "movement.xiangqi.king": (
            "Moves one step orthogonally inside its 3×3 palace. In this version, "
            "the two generals may face on an open file."
        ),
        "movement.chess.king": "Moves one step in any direction.",
        "play.title": "Match in progress",
        "play.turn": "Turn: {side}",
        "play.checked": "{side} is in check!",
        "play.rules": "Game rules",
        "play.rule.moves": "• Green: move; red ring: capture",
        "play.rule.king": "• Capture the king to win; no checkmate rule",
        "play.rule.promotion": "• Chess pawns promote on the last row",
        "play.rule.xiangqi": "• Horse-leg and cannon-screen rules apply",
        "play.status": "Status",
        "play.ai_opponent": "Opponent: Simple AI",
        "play.escape": "ESC to return to the main menu",
        "handoff.red.title": "Red setup complete",
        "handoff.red.body": "Red should step away, then hand the computer to Black.",
        "handoff.red.button": "I am Black — start setup",
        "handoff.play.title": "Both armies are ready",
        "handoff.play.body": "The armies will be revealed together. Red moves first.",
        "handoff.play.button": "Reveal armies and start",
        "handoff.privacy": "The previous player's army is hidden on this screen",
        "promotion.title": "Pawn reached the last row: choose a promotion",
        "promotion.queen": "Q Queen",
        "promotion.rook": "R Rook",
        "promotion.bishop": "B Bishop",
        "promotion.knight": "N Knight",
        "game_over.title": "Game over",
        "game_over.winner": "{side} wins!",
        "game_over.draw": "Draw",
        "game_over.reason.king_capture": "The opposing king was captured",
        "game_over.reason.no_legal_moves": "The opponent has no legal move",
        "game_over.reason.threefold_repetition": "The position repeated three times",
        "game_over.reason.move_limit": (
            "100 plies passed without a capture or pawn move"
        ),
        "game_over.reason.resignation": "The opponent resigned",
        "game_over.restart": "Play again",
        "game_over.menu": "Main menu",
    },
    "fr": {
        "window_title": "Confluence des échecs",
        "menu.title": "Confluence des échecs",
        "menu.subtitle": "Xiangqi × Échecs",
        "menu.budget": "points de départ",
        "menu.rulesets": "règles de pièces",
        "menu.king": "roi à protéger",
        "menu.start": "Commencer une partie locale",
        "menu.mode.single": "Solo · IA simple",
        "menu.mode.local": "Deux joueurs locaux",
        "menu.start.single": "Commencer une partie solo",
        "menu.start.local": "Commencer une partie locale",
        "menu.tagline": "Composez vos armées secrètes et capturez le roi adverse",
        "menu.escape": "Échap pour quitter",
        "side.red": "Rouges",
        "side.black": "Noirs",
        "game.xiangqi": "Xiangqi",
        "game.chess": "Échecs",
        "piece.xiangqi.bing": "soldat",
        "piece.xiangqi.advisor": "conseiller",
        "piece.xiangqi.elephant": "éléphant",
        "piece.xiangqi.horse": "cheval",
        "piece.xiangqi.cannon": "canon",
        "piece.xiangqi.rook": "char",
        "piece.xiangqi.king": "général",
        "piece.chess.pawn": "pion",
        "piece.chess.knight": "cavalier",
        "piece.chess.bishop": "fou",
        "piece.chess.rook": "tour",
        "piece.chess.queen": "dame",
        "piece.chess.king": "roi",
        "status.setup.red": "Rouges : déployez dans vos quatre rangées arrière.",
        "status.setup.black": (
            "Noirs : choisissez et placez vos pièces dans votre zone."
        ),
        "status.catalog_selected": (
            "{piece} sélectionné ; cliquez dans la zone éclairée."
        ),
        "status.buy_unavailable": "Fonds insuffisants ou limite d’achat atteinte.",
        "status.play_start": "Les Rouges commencent. Sélectionnez une pièce.",
        "status.piece_selected": "{piece} sélectionné.",
        "status.no_piece": "Aucune de vos pièces jouables ne se trouve ici.",
        "status.choose_catalog": "Choisissez d’abord une pièce dans la boutique.",
        "status.deployment_only": "Placez les pièces dans votre zone de déploiement.",
        "status.occupied": "Cette position est déjà occupée.",
        "status.cannot_buy": "Vous ne pouvez plus acheter cette pièce.",
        "status.placed": "{piece} placé. Il reste {budget} points.",
        "status.remove_hint": "Clic droit sur une pièce achetée pour la rembourser.",
        "status.king_fixed": "Utilisez les options Roi pour le déplacer ou le changer.",
        "status.king_selected": "{piece} : choisissez une case autorisée.",
        "status.king_upgrade_unavailable": (
            "Il faut encore 3 points pour choisir le roi d’échecs."
        ),
        "status.king_place_xiangqi": (
            "Le général doit être placé dans votre palais 3×3."
        ),
        "status.king_place_chess": "Placez le roi dans vos quatre rangées arrière.",
        "status.king_placed": "{piece} placé.",
        "status.removed": "{piece} retiré ; {cost} points remboursés.",
        "status.promote": "Pion arrivé : choisissez sa promotion.",
        "status.turn": "Aux {side} de jouer.",
        "status.ai_ready": "L’IA a terminé son déploiement secret. Aux Rouges.",
        "status.ai_thinking": "L’IA réfléchit…",
        "status.ai_moved": ("L’IA déplace {piece} en ({column}, {row}). Aux Rouges."),
        "setup.title": "{side} — déploiement secret",
        "setup.budget": "Budget  {budget} / {total}",
        "setup.count": "Pièces  {count} / {maximum}",
        "setup.instructions": "Sélectionnez puis placez ; clic droit pour rembourser",
        "setup.king_label": "Roi",
        "setup.king.xiangqi": "Général xiangqi",
        "setup.king.chess": "Roi d’échecs (+3)",
        "setup.shop": "Boutique de pièces",
        "setup.price": "{cost} pts   {count}/{limit}",
        "setup.movement": "Déplacement : {piece}",
        "setup.preview.move": "déplacement",
        "setup.preview.capture": "prise seule",
        "setup.preview.screen": "écran",
        "setup.preview.blocker": "obstacle",
        "setup.preview.before_river": "Avant la rivière",
        "setup.preview.after_river": "Après la rivière",
        "setup.preview.first_move": "Deux cases au 1er coup seulement",
        "setup.preview.last_row": "Promotion sur la dernière rangée",
        "setup.preview.double_only": "anneau = double initial",
        "setup.preview.facing_allowed": "Face-à-face autorisé",
        "setup.finish": "Confirmer et passer la main",
        "movement.xiangqi.bing": (
            "Avance d’une case ; après la rivière, se déplace aussi de côté. Ne recule "
            "jamais."
        ),
        "movement.xiangqi.advisor": (
            "Avance d’une case en diagonale. Dans ce jeu, il peut quitter le palais."
        ),
        "movement.xiangqi.elephant": (
            "Avance de deux cases en diagonale sans sauter un œil bloqué. Il peut "
            "traverser la rivière."
        ),
        "movement.xiangqi.horse": (
            "Se déplace en L, mais une pièce placée contre sa jambe le bloque."
        ),
        "movement.xiangqi.cannon": (
            "Glisse en ligne droite. Pour prendre, il doit sauter exactement un écran."
        ),
        "movement.xiangqi.rook": (
            "Glisse sur les lignes et colonnes sans pouvoir sauter de pièce."
        ),
        "movement.chess.pawn": (
            "Avance d’une case, ou deux seulement au premier coup ; prend en "
            "diagonale et doit être promu sur la dernière rangée."
        ),
        "movement.chess.knight": "Saute en L : deux cases, puis une.",
        "movement.chess.bishop": ("Glisse en diagonale sans pouvoir sauter de pièce."),
        "movement.chess.rook": (
            "Glisse sur les lignes et colonnes sans pouvoir sauter de pièce."
        ),
        "movement.chess.queen": (
            "Glisse sur les lignes, colonnes ou diagonales sans sauter de pièce."
        ),
        "movement.xiangqi.king": (
            "Avance d’une case en ligne droite dans son palais 3×3. Dans cette "
            "version, les deux généraux peuvent se faire face."
        ),
        "movement.chess.king": "Avance d’une case dans toutes les directions.",
        "play.title": "Partie en cours",
        "play.turn": "Tour : {side}",
        "play.checked": "Les {side} sont en échec !",
        "play.rules": "Règles de la partie",
        "play.rule.moves": "• Vert : déplacer ; cercle rouge : capturer",
        "play.rule.king": "• Capturez le roi ; pas de règle d’échec et mat",
        "play.rule.promotion": "• Les pions sont promus sur la dernière rangée",
        "play.rule.xiangqi": "• Règles de jambe du cheval et d’écran du canon",
        "play.status": "État",
        "play.ai_opponent": "Adversaire : IA simple",
        "play.escape": "Échap pour revenir au menu principal",
        "handoff.red.title": "Déploiement des Rouges terminé",
        "handoff.red.body": (
            "Les Rouges s’éloignent puis passent l’ordinateur aux Noirs."
        ),
        "handoff.red.button": "Je suis Noir — déployer",
        "handoff.play.title": "Les deux armées sont prêtes",
        "handoff.play.body": "Les armées vont être révélées. Les Rouges commencent.",
        "handoff.play.button": "Révéler et commencer",
        "handoff.privacy": "L’armée du joueur précédent reste cachée sur cet écran",
        "promotion.title": "Pion sur la dernière rangée : choisissez sa promotion",
        "promotion.queen": "D Dame",
        "promotion.rook": "T Tour",
        "promotion.bishop": "F Fou",
        "promotion.knight": "C Cavalier",
        "game_over.title": "Partie terminée",
        "game_over.winner": "Les {side} gagnent !",
        "game_over.draw": "Partie nulle",
        "game_over.reason.king_capture": "Le roi adverse a été capturé",
        "game_over.reason.no_legal_moves": "L’adversaire n’a aucun coup légal",
        "game_over.reason.threefold_repetition": "La position s’est répétée trois fois",
        "game_over.reason.move_limit": (
            "100 demi-coups sans prise ni mouvement de pion"
        ),
        "game_over.reason.resignation": "L’adversaire a abandonné",
        "game_over.restart": "Rejouer",
        "game_over.menu": "Menu principal",
    },
}


def translate(language: Language, key: str, **values: object) -> str:
    """Translate and format a UI message."""
    return TRANSLATIONS[language][key].format(**values)
