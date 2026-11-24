"""
德州扑克 - Pygame 主程序
Texas Hold'em with AI players of different styles.
Run: python main.py
"""

import sys
import os
import json
import math
import random
import webbrowser
import pygame

from cards import Deck
from player import AIPlayer, HumanPlayer, AI_PROFILES, POSITION_NAMES_ZH, Player
from game import PokerGame
from hand_evaluator import HAND_NAMES_ZH
import gui_renderer as gr
from music_manager import MusicManager, TRACKS


# 窗口设置
WIN_W = 1280
WIN_H = 800
TABLE_CX = 620
TABLE_CY = 380
TABLE_RX = 330
TABLE_RY = 215
SEAT_OFFSET = 55
FPS = 30

# 座位角度 (6人桌, 0号位在正下方)
SEAT_ANGLES = [90, 150, 210, 270, 330, 30]

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
GUIDE_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '玩家指南.pdf')

AI_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank']
AI_STYLE_KEYS = ['rock', 'shark', 'station', 'maniac', 'balanced', 'nit']


def calc_seat_pos(angle, num=6):
    """计算座位坐标"""
    rad = math.radians(angle)
    sx = TABLE_CX + (TABLE_RX + SEAT_OFFSET) * math.cos(rad)
    sy = TABLE_CY + (TABLE_RY + SEAT_OFFSET) * math.sin(rad)
    # 居中面板
    sx -= gr.SEAT_W // 2
    sy -= gr.SEAT_H // 2
    # 边界修正
    sx = max(5, min(WIN_W - gr.SEAT_W - 5, sx))
    sy = max(5, min(WIN_H - gr.SEAT_H - 130, sy))
    return (int(sx), int(sy))


def seat_angles(num_seats):
    """生成 num_seats 个座位的角度 (0号位正下方, 与6人桌原始角度兼容)"""
    if num_seats == 6:
        return SEAT_ANGLES[:]
    step = 360 / num_seats
    return [int((90 + i * step) % 360) for i in range(num_seats)]


# ---------------------------------------------------------------------------
# 设置
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    'num_seats': 6,
    'seat_styles': ['balanced', 'shark', 'station', 'maniac', 'rock', 'nit'],
    'initial_chips': 1000,
    'small_blind': 10,
    'volume': 0.5,
    'music_enabled': True,
    'track_idx': 0,
}


class Settings:
    """游戏设置 (内存中持有, 自动持久化到 config.json)"""

    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            for k, v in saved.items():
                if k in self.data:
                    self.data[k] = v
        except (OSError, json.JSONDecodeError):
            pass
        self.normalize()

    def save(self):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def normalize(self):
        """约束设置到合法范围"""
        d = self.data
        d['num_seats'] = max(2, min(6, int(d['num_seats'])))
        styles = list(d.get('seat_styles', []))
        while len(styles) < 6:
            styles.append(AI_STYLE_KEYS[len(styles) % len(AI_STYLE_KEYS)])
        d['seat_styles'] = [s if s in AI_PROFILES else 'balanced' for s in styles[:6]]
        d['initial_chips'] = max(100, min(100000, int(d['initial_chips'])))
        # 大盲至少是小盲两倍, 且不超过初始资金的 1/2, 保证游戏可进行
        sb_max = max(5, d['initial_chips'] // 4)
        d['small_blind'] = max(5, min(sb_max, int(d['small_blind'])))
        d['volume'] = max(0.0, min(1.0, float(d['volume'])))
        d['music_enabled'] = bool(d['music_enabled'])
        d['track_idx'] = int(d['track_idx']) % len(TRACKS)

    @property
    def num_seats(self):
        return self.data['num_seats']

    @property
    def seat_styles(self):
        return self.data['seat_styles']

    @property
    def initial_chips(self):
        return self.data['initial_chips']

    @property
    def big_blind(self):
        return self.data['small_blind'] * 2


# ---------------------------------------------------------------------------
# 通用界面小组件
# ---------------------------------------------------------------------------

class Button:
    """简单按钮"""

    def __init__(self, rect, text, font_key='medium', base=(30, 60, 40),
                 hover=(45, 90, 55), border=gr.TEXT_GOLD, text_color=gr.TEXT_WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font_key = font_key
        self.base = base
        self.hover = hover
        self.border = border
        self.text_color = text_color

    def draw(self, surface, fonts, mouse_pos):
        color = self.hover if self.rect.collidepoint(mouse_pos) else self.base
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border, self.rect, 2, border_radius=8)
        font = fonts[self.font_key]
        surf = font.render(self.text, True, self.text_color)
        surface.blit(surf, (self.rect.centerx - surf.get_width() // 2,
                            self.rect.centery - surf.get_height() // 2))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and \
            self.rect.collidepoint(event.pos)


# ---------------------------------------------------------------------------
# 游戏控制器 (观看AI / 人类参与 两种模式)
# ---------------------------------------------------------------------------

class GameApp:
    """单局游戏控制器。mode: 'watch' (观看AI) | 'play' (人类参与)"""

    def __init__(self, settings, mode, fonts):
        self.settings = settings
        self.mode = mode
        self.fonts = fonts

        # 构建玩家 (0号位=正下方; 参与模式时0号位为人类)
        n = settings.num_seats
        styles = settings.seat_styles
        self.players = []
        names = AI_NAMES[:]
        random.shuffle(names)
        name_i = 0
        for seat in range(n):
            if mode == 'play' and seat == 0:
                self.players.append(HumanPlayer('你', chips=settings.initial_chips))
            else:
                self.players.append(AIPlayer(names[name_i % len(names)], styles[seat],
                                             chips=settings.initial_chips,
                                             seed=random.randint(0, 99999)))
                name_i += 1

        self.game = PokerGame(self.players,
                              small_blind=settings.data['small_blind'],
                              big_blind=settings.big_blind)

        # 游戏控制
        self.paused = False
        self.speed = 1.0
        self.action_timer = 0.0
        self.result_timer = 0.0
        self.state = 'idle'  # idle, playing, results, game_over
        self.last_log_count = 0
        self.current_player_idx = -1

        # 人类玩家输入
        self.awaiting_human = False
        self.human_raise_to = 0
        self.exit_to_menu = False

        # 座位坐标
        self.seat_positions = [calc_seat_pos(a) for a in seat_angles(n)]

        # 开始第一手
        self.start_new_hand()

    # ---------------- 游戏流程 (保持原有结构) ----------------

    def start_new_hand(self):
        """开始新一手"""
        # 检查是否有玩家被淘汰
        active_count = sum(1 for p in self.players if p.chips > 0)
        if active_count < 2:
            self.state = 'game_over'
            return

        self.game.start_new_hand()
        self.state = 'playing'
        self.action_timer = 0.6 / self.speed
        self.last_log_count = 0
        self.current_player_idx = -1
        self.awaiting_human = False

    def update(self, dt):
        """更新游戏逻辑"""
        if self.paused:
            return
        if self.awaiting_human:
            return  # 等待人类玩家输入

        if self.state == 'playing':
            self.action_timer -= dt
            if self.action_timer > 0:
                return

            self.step_game()
        elif self.state == 'results':
            self.result_timer -= dt
            if self.result_timer <= 0:
                self.start_new_hand()

    def step_game(self):
        """推进一步游戏"""
        game = self.game

        # 手牌是否结束
        if game.is_hand_complete():
            self.state = 'results'
            self.result_timer = 4.0 / self.speed
            return

        # 检查下注轮是否结束
        if game.is_betting_round_complete():
            # 检查是否只剩一人
            active = [p for p in game.players if not p.is_folded]
            if len(active) <= 1:
                game.showdown()
                self.state = 'results'
                self.result_timer = 3.0 / self.speed
                return
            # 进入下一轮
            game.advance_round()
            self.action_timer = 1.0 / self.speed
            return

        # 获取当前需要行动的玩家
        result = game.get_player_to_act()
        if result is None:
            # 没有人需要行动, 进入下一轮
            if not game.is_hand_complete():
                game.advance_round()
                self.action_timer = 1.0 / self.speed
            else:
                self.state = 'results'
                self.result_timer = 3.0 / self.speed
            return

        idx, player = result
        self.current_player_idx = idx

        # AI 决策
        if isinstance(player, AIPlayer):
            gs = game.get_game_state_for(idx)
            action, amount = player.make_decision(gs)
            game.apply_action(idx, action, amount)
            self.action_timer = 0.8 / self.speed
        elif isinstance(player, HumanPlayer):
            # 等待人类输入, 由界面层调用 apply_human_action
            self.awaiting_human = True
            self._init_human_raise_amount(player)
        else:
            # 未知玩家类型, 默认弃牌
            game.apply_action(idx, 'fold')
            self.action_timer = 0.5 / self.speed

    # ---------------- 人类玩家行动 ----------------

    def human_player(self):
        for p in self.players:
            if isinstance(p, HumanPlayer):
                return p
        return None

    def _init_human_raise_amount(self, player):
        """人类行动时初始化默认加注目标"""
        game = self.game
        to_call = max(0, game.current_bet - player.current_bet)
        min_total = game.current_bet + game.min_raise if to_call > 0 or game.current_bet > 0 \
            else game.min_raise
        max_total = player.current_bet + player.chips
        self.human_raise_to = min(min_total, max_total)

    def apply_human_action(self, action):
        """应用人类玩家动作, action: 'fold' | 'check_call' | 'raise' | 'all_in'"""
        if not self.awaiting_human:
            return
        idx = self.current_player_idx
        player = self.players[idx]
        game = self.game
        to_call = max(0, game.current_bet - player.current_bet)

        if action == 'fold':
            game.apply_action(idx, 'fold')
        elif action == 'check_call':
            if to_call <= 0:
                game.apply_action(idx, 'check')
            elif to_call >= player.chips:
                game.apply_action(idx, 'call')  # bet() 自动处理全压跟注
            else:
                game.apply_action(idx, 'call', to_call)
        elif action == 'raise':
            max_total = player.current_bet + player.chips
            target = max(self.human_raise_to, min(game.current_bet + game.min_raise, max_total))
            amount = target - player.current_bet
            if target >= max_total and player.chips <= amount:
                game.apply_action(idx, 'all_in', player.chips)
            else:
                game.apply_action(idx, 'raise', amount)
        elif action == 'all_in':
            game.apply_action(idx, 'all_in', player.chips)

        self.awaiting_human = False
        self.action_timer = 0.8 / self.speed

    def adjust_human_raise(self, delta):
        """调整加注目标 (delta 为大盲倍数步进)"""
        if not self.awaiting_human:
            return
        player = self.players[self.current_player_idx]
        game = self.game
        step = max(1, game.big_blind)
        min_total = game.current_bet + game.min_raise
        max_total = player.current_bet + player.chips
        self.human_raise_to = max(min_total, min(max_total, self.human_raise_to + delta * step))

    def human_button_rects(self):
        """人类行动按钮布局, 返回 {action: Rect}"""
        labels = self.human_button_labels()
        w, h = 150, 44
        gap = 14
        total = len(labels) * w + (len(labels) - 1) * gap
        x0 = (WIN_W - total) // 2
        y = WIN_H - h - 18
        rects = {}
        for i, key in enumerate(labels):
            rects[key] = pygame.Rect(x0 + i * (w + gap), y, w, h)
        return rects

    def human_button_labels(self):
        """返回行动按钮顺序 (raise 按钮旁有 -/+ 小按钮, 由渲染与点击共同使用)"""
        return ['fold', 'check_call', 'raise_minus', 'raise', 'raise_plus', 'all_in']

    def human_button_text(self, key):
        player = self.players[self.current_player_idx]
        game = self.game
        to_call = max(0, game.current_bet - player.current_bet)
        if key == 'fold':
            return '弃牌'
        if key == 'check_call':
            if to_call <= 0:
                return '过牌'
            if to_call >= player.chips:
                return f'跟注(全压) ${player.chips}'
            return f'跟注 ${to_call}'
        if key == 'raise':
            return f'加注到 ${self.human_raise_to}'
        if key == 'all_in':
            return f'全压 ${player.chips}'
        return ''

    # ---------------- 渲染 (保持原有结构) ----------------

    def render(self, screen):
        """渲染画面"""
        screen.fill(gr.BG_COLOR)

        # 绘制桌面
        gr.draw_table(screen, TABLE_CX, TABLE_CY, TABLE_RX, TABLE_RY)

        # 绘制庄家标记位置 (在桌面边缘)
        dealer_pos = self.calc_dealer_btn_pos()
        if dealer_pos:
            dx, dy = dealer_pos
            pygame.draw.circle(screen, (255, 255, 255), (dx, dy), 14)
            pygame.draw.circle(screen, (40, 40, 40), (dx, dy), 14, 2)
            d_surf = self.fonts['tiny'].render("D", True, (40, 40, 40))
            screen.blit(d_surf, (dx - 4, dy - 6))

        # 绘制公共牌
        gr.draw_community(screen, self.game.community, TABLE_CX, TABLE_CY, self.fonts)

        # 绘制底池
        if self.game.pot > 0:
            gr.draw_pot(screen, self.game.pot, TABLE_CX, TABLE_CY, self.fonts)

        # 绘制玩家座位 (参与模式下隐藏对手底牌, 摊牌后亮出)
        human = self.human_player()
        reveal = (self.state == 'results')
        for i, player in enumerate(self.players):
            if i >= len(self.seat_positions):
                continue
            x, y = self.seat_positions[i]
            is_current = (i == self.current_player_idx and self.state == 'playing')
            is_dealer = (i == self.game.dealer_idx)
            face_up = True
            if self.mode == 'play' and player is not human:
                face_up = reveal
            gr.draw_seat(screen, player, x, y, is_current, is_dealer, self.fonts,
                         show_cards=True, face_up_cards=face_up)

        # 绘制轮次指示
        gr.draw_round_indicator(screen, self.game.round_name, 10, 10, self.fonts)

        # 绘制日志面板
        gr.draw_log_panel(screen, self.game.log, WIN_W - 210, 50, 200, 500, self.fonts)

        # 绘制赢家信息
        if self.state == 'results' and self.game.winners:
            gr.draw_winners(screen, self.game.winners, TABLE_CX, TABLE_CY, self.fonts)

        # 游戏结束
        if self.state == 'game_over':
            champ = max(self.players, key=lambda p: p.chips)
            text = f"游戏结束! 冠军: {champ.name} (${champ.chips})"
            surf = self.fonts['big'].render(text, True, gr.TEXT_GOLD)
            screen.blit(surf, (WIN_W // 2 - surf.get_width() // 2, WIN_H // 2))
            hint = self.fonts['small'].render("按 ESC 返回主菜单", True, gr.TEXT_WHITE)
            screen.blit(hint, (WIN_W // 2 - hint.get_width() // 2, WIN_H // 2 + 44))

        # 人类行动按钮
        if self.awaiting_human:
            self.render_human_controls(screen)

        # 绘制控制提示
        if self.mode == 'watch':
            gr.draw_controls_hint(screen, self.fonts)
            gr.draw_speed_indicator(screen, self.speed, self.fonts)
        else:
            hint = self.fonts['tiny'].render("ESC: 返回主菜单", True, gr.TEXT_GRAY)
            screen.blit(hint, (10, WIN_H - 24))

        # 暂停标记
        if self.paused:
            pause_surf = self.fonts['big'].render("|| 已暂停", True, gr.TEXT_GOLD)
            screen.blit(pause_surf, (WIN_W // 2 - pause_surf.get_width() // 2, WIN_H - 60))

    def render_human_controls(self, screen):
        """绘制人类玩家的行动按钮"""
        rects = self.human_button_rects()
        mouse = pygame.mouse.get_pos()
        small_font = self.fonts['tiny']
        for key, rect in rects.items():
            if key in ('raise_minus', 'raise_plus'):
                # 小的加减按钮紧贴加注按钮两侧
                label = '−' if key == 'raise_minus' else '+'
                pygame.draw.rect(screen, (35, 70, 45), rect, border_radius=8)
                pygame.draw.rect(screen, gr.TEXT_GOLD, rect, 2, border_radius=8)
                surf = self.fonts['medium'].render(label, True, gr.TEXT_WHITE)
                screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                   rect.centery - surf.get_height() // 2))
                continue
            text = self.human_button_text(key)
            if not text:
                continue
            color = (45, 90, 55) if rect.collidepoint(mouse) else (30, 60, 40)
            if key == 'fold':
                color = (110, 40, 40) if rect.collidepoint(mouse) else (90, 35, 35)
            if key == 'all_in':
                color = (110, 35, 110) if rect.collidepoint(mouse) else (90, 30, 90)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, gr.TEXT_GOLD, rect, 2, border_radius=8)
            surf = self.fonts['small'].render(text, True, gr.TEXT_WHITE)
            screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                               rect.centery - surf.get_height() // 2))

    def calc_dealer_btn_pos(self):
        """计算庄家按钮位置 (在对应座位附近的桌面上)"""
        if self.game.dealer_idx >= len(self.seat_positions):
            return None
        angle = seat_angles(self.settings.num_seats)[self.game.dealer_idx]
        rad = math.radians(angle)
        # 庄家按钮放在桌面边缘内侧
        dx = TABLE_CX + TABLE_RX * 0.75 * math.cos(rad)
        dy = TABLE_CY + TABLE_RY * 0.75 * math.sin(rad)
        return (int(dx), int(dy))

    # ---------------- 输入 ----------------

    def handle_event(self, event):
        """处理输入事件, 返回 False 表示请求退出到主菜单"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            elif event.key == pygame.K_SPACE and self.mode == 'watch':
                self.paused = not self.paused
            elif event.key == pygame.K_n:
                # 手动开始下一手
                if self.state == 'results' or self.state == 'idle':
                    self.start_new_hand()
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                self.speed = min(5.0, self.speed + 0.5)
            elif event.key == pygame.K_MINUS:
                self.speed = max(0.5, self.speed - 0.5)

        if self.awaiting_human and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = self.human_button_rects()
            if rects['fold'].collidepoint(event.pos):
                self.apply_human_action('fold')
            elif rects['check_call'].collidepoint(event.pos):
                self.apply_human_action('check_call')
            elif rects['all_in'].collidepoint(event.pos):
                self.apply_human_action('all_in')
            elif rects['raise'].collidepoint(event.pos):
                self.apply_human_action('raise')
            elif rects['raise_minus'].collidepoint(event.pos):
                self.adjust_human_raise(-1)
            elif rects['raise_plus'].collidepoint(event.pos):
                self.adjust_human_raise(1)
        return True


# ---------------------------------------------------------------------------
# 主菜单
# ---------------------------------------------------------------------------

class MenuScreen:
    """主界面: 开始游戏(两种模式) / 设置 / 退出 / 玩家指南"""

    def __init__(self, app):
        self.app = app
        fonts = app.fonts
        cx = WIN_W // 2
        bw, bh, gap = 300, 56, 22
        y0 = 300
        self.buttons = {
            'watch': Button((cx - bw // 2, y0, bw, bh), '观看 AI 对战', 'large'),
            'play':  Button((cx - bw // 2, y0 + (bh + gap), bw, bh), '亲自参与对战', 'large'),
            'settings': Button((cx - bw // 2, y0 + 2 * (bh + gap), bw, bh), '设置', 'large'),
            'quit':  Button((cx - bw // 2, y0 + 3 * (bh + gap), bw, bh), '退出游戏', 'large',
                            base=(70, 35, 35), hover=(95, 45, 45)),
        }
        self.guide_btn = Button((WIN_W - 220, WIN_H - 80, 200, 46), '玩家指南 (PDF)',
                                'medium', base=(40, 55, 90), hover=(55, 75, 120))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.begin_quit()
            return
        for key, btn in self.buttons.items():
            if btn.clicked(event):
                if key == 'watch':
                    self.app.start_game('watch')
                elif key == 'play':
                    self.app.start_game('play')
                elif key == 'settings':
                    self.app.show_settings()
                elif key == 'quit':
                    self.app.begin_quit()
        if self.guide_btn.clicked(event):
            pdf_path = GUIDE_PDF
            if os.path.exists(pdf_path):
                webbrowser.open('file://' + pdf_path)
            else:
                self.app.flash_message('未找到 玩家指南.pdf')

    def render(self, screen):
        screen.fill(gr.BG_COLOR)
        fonts = self.app.fonts
        mouse = pygame.mouse.get_pos()

        # 标题
        title = fonts['big'].render('德州扑克', True, gr.TEXT_GOLD)
        screen.blit(title, (WIN_W // 2 - title.get_width() // 2, 110))
        sub = fonts['medium'].render('Texas Hold\'em · AI 对战模拟器', True, gr.TEXT_GRAY)
        screen.blit(sub, (WIN_W // 2 - sub.get_width() // 2, 165))

        # 装饰牌桌
        gr.draw_table(screen, WIN_W // 2, 190, 260, 60)

        for btn in self.buttons.values():
            btn.draw(screen, fonts, mouse)
        self.guide_btn.draw(screen, fonts, mouse)

        # 左下角音乐状态
        music = self.app.music
        note = f"♪ {music.current_name()}" + ("" if music.enabled else " (已静音)")
        surf = fonts['tiny'].render(note, True, gr.TEXT_GRAY)
        screen.blit(surf, (12, WIN_H - 24))

        self.app.render_flash(screen)


# ---------------------------------------------------------------------------
# 设置界面
# ---------------------------------------------------------------------------

class SettingsScreen:
    """设置: 座位数 / 每座AI类型 / 初始资金 / 盲注 / 音乐"""

    def __init__(self, app):
        self.app = app
        self.settings = app.settings
        fonts = app.fonts
        self.back_btn = Button((WIN_W // 2 - 100, WIN_H - 90, 200, 50), '返回主菜单', 'large')

        # 音量滑条
        self.slider_rect = pygame.Rect(0, 0, 260, 14)
        self.dragging = False
        self.rebuild_rows()

    def rebuild_rows(self):
        """根据当前设置重建控件行"""
        fonts = self.app.fonts
        s = self.settings
        self.rows = []  # (label, [(btn_key, text, Rect) ...])
        cx = 340
        xw = 560

        def row(label, controls):
            self.rows.append((label, controls))

        row('座位数', [
            ('seats_minus', '−'), ('seats_val', str(s.num_seats)), ('seats_plus', '+'),
        ])
        for i in range(s.num_seats):
            style_key = s.data['seat_styles'][i]
            name_zh = AI_PROFILES[style_key][3]
            row(f'座位 {i} 对手', [('style_%d' % i, f'[{name_zh}]')])
        row('初始资金', [
            ('chips_minus', '−'), ('chips_val', f"${s.data['initial_chips']}"), ('chips_plus', '+'),
        ])
        row('小盲注', [
            ('sb_minus', '−'), ('sb_val', f"${s.data['small_blind']}"), ('sb_plus', '+'),
        ])
        row('大盲注', [('bb_val', f"${s.big_blind} (自动 = 小盲×2)")])
        row('音乐', [
            ('music_toggle', '开' if s.data['music_enabled'] else '关'),
            ('track_name', s_track_name(s)),
            ('music_next', '下一首'),
        ])
        row('音量', [])  # 滑条单独绘制

        # 生成按钮矩形
        y = 118
        for label, controls in self.rows:
            rects = []
            x = xw
            for key, text in controls:
                w = max(64, 18 * len(text) + 28) if key.endswith('val') or key == 'track_name' else 46
                if key == 'track_name':
                    w = 260
                rects.append((key, text, pygame.Rect(x, y, w, 40)))
                x += w + 10
            self.rows[self.rows.index((label, controls))] = (label, rects)
            y += 52

        # 音量滑条位置 (音量行)
        self.slider_rect = pygame.Rect(xw, y + 12, 260, 14)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.show_menu()
            return
        if self.back_btn.clicked(event):
            self.app.show_menu()
            return

        s = self.settings
        d = s.data

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.slider_rect.collidepoint(event.pos):
                self.dragging = True
                self._set_volume_from_x(event.pos[0])
                return
            for label, controls in self.rows:
                for key, text, rect in controls:
                    if rect.collidepoint(event.pos):
                        self._on_control(key)
                        return
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_volume_from_x(event.pos[0])

    def _set_volume_from_x(self, x):
        ratio = (x - self.slider_rect.x) / self.slider_rect.width
        self.app.set_volume(ratio)

    def _on_control(self, key):
        s = self.settings
        d = s.data
        if key == 'seats_minus':
            d['num_seats'] = max(2, s.num_seats - 1)
        elif key == 'seats_plus':
            d['num_seats'] = min(6, s.num_seats + 1)
        elif key.startswith('style_'):
            i = int(key.split('_')[1])
            cur = d['seat_styles'][i]
            nxt = AI_STYLE_KEYS[(AI_STYLE_KEYS.index(cur) + 1) % len(AI_STYLE_KEYS)]
            d['seat_styles'][i] = nxt
        elif key == 'chips_minus':
            d['initial_chips'] = max(100, d['initial_chips'] - 100)
        elif key == 'chips_plus':
            d['initial_chips'] = min(100000, d['initial_chips'] + 100)
        elif key == 'sb_minus':
            d['small_blind'] = max(5, d['small_blind'] - 5)
        elif key == 'sb_plus':
            d['small_blind'] = min(500, d['small_blind'] + 5)
        elif key == 'music_toggle':
            self.app.music.toggle()
            d['music_enabled'] = self.app.music.enabled
        elif key == 'music_next':
            self.app.music.next_track()
            d['track_idx'] = self.app.music.track_idx
        s.normalize()
        s.save()
        self.rebuild_rows()

    def render(self, screen):
        screen.fill(gr.BG_COLOR)
        fonts = self.app.fonts
        mouse = pygame.mouse.get_pos()

        title = fonts['big'].render('设置', True, gr.TEXT_GOLD)
        screen.blit(title, (WIN_W // 2 - title.get_width() // 2, 40))

        label_x = 130
        for label, controls in self.rows:
            if not controls:
                continue  # 音量行: 标签与滑条单独绘制
            surf = fonts['medium'].render(label, True, gr.TEXT_WHITE)
            screen.blit(surf, (label_x, controls[0][2].centery - surf.get_height() // 2))
            for key, text, rect in controls:
                if key.endswith('val') or key == 'track_name':
                    pygame.draw.rect(screen, (15, 30, 20), rect, border_radius=6)
                    pygame.draw.rect(screen, (60, 100, 70), rect, 1, border_radius=6)
                    surf = fonts['small'].render(text, True, gr.TEXT_GOLD)
                    screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                       rect.centery - surf.get_height() // 2))
                else:
                    color = (45, 90, 55) if rect.collidepoint(mouse) else (30, 60, 40)
                    pygame.draw.rect(screen, color, rect, border_radius=8)
                    pygame.draw.rect(screen, gr.TEXT_GOLD, rect, 2, border_radius=8)
                    surf = fonts['medium'].render(text, True, gr.TEXT_WHITE)
                    screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                       rect.centery - surf.get_height() // 2))

        # 音量滑条 (音量行)
        vol_surf = fonts['medium'].render('音量', True, gr.TEXT_WHITE)
        screen.blit(vol_surf, (label_x, self.slider_rect.centery - vol_surf.get_height() // 2))
        pygame.draw.rect(screen, (15, 30, 20), self.slider_rect, border_radius=7)
        ratio = self.app.music.volume
        fill = pygame.Rect(self.slider_rect.x, self.slider_rect.y,
                           int(self.slider_rect.width * ratio), self.slider_rect.height)
        pygame.draw.rect(screen, (60, 140, 80), fill, border_radius=7)
        pygame.draw.rect(screen, gr.TEXT_GOLD, self.slider_rect, 2, border_radius=7)
        pct = fonts['small'].render(f'{int(ratio * 100)}%', True, gr.TEXT_WHITE)
        screen.blit(pct, (self.slider_rect.right + 12, self.slider_rect.centery - pct.get_height() // 2))

        self.back_btn.draw(screen, fonts, mouse)
        self.app.render_flash(screen)


def s_track_name(settings):
    return TRACKS[settings.data['track_idx'] % len(TRACKS)]


# ---------------------------------------------------------------------------
# 应用总控: 场景切换 + 退出渐暗
# ---------------------------------------------------------------------------

class App:
    """场景管理器: menu / settings / game"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("德州扑克")
        self.clock = pygame.time.Clock()
        self.fonts = gr.init_fonts()

        self.settings = Settings()
        self.music = MusicManager(volume=self.settings.data['volume'],
                                  enabled=self.settings.data['music_enabled'])
        self.music.track_idx = self.settings.data['track_idx']

        self.scene = 'menu'
        self.menu = MenuScreen(self)
        self.settings_screen = None
        self.game = None

        self.flash_text = ''
        self.flash_timer = 0.0

        # 退出渐暗
        self.quitting = False
        self.fade_alpha = 0.0
        self.running = True

    # ---------- 场景切换 ----------

    def show_menu(self):
        self.settings.save()
        self.scene = 'menu'

    def show_settings(self):
        self.settings_screen = SettingsScreen(self)
        self.scene = 'settings'

    def start_game(self, mode):
        self.settings.save()
        self.game = GameApp(self.settings, mode, self.fonts)
        self.scene = 'game'

    # ---------- 通用 ----------

    def set_volume(self, ratio):
        self.music.set_volume(ratio)
        self.settings.data['volume'] = self.music.volume
        self.settings.save()

    def flash_message(self, text, seconds=2.5):
        self.flash_text = text
        self.flash_timer = seconds

    def render_flash(self, screen):
        if self.flash_timer > 0 and self.flash_text:
            surf = self.fonts['small'].render(self.flash_text, True, gr.TEXT_RED)
            screen.blit(surf, (WIN_W // 2 - surf.get_width() // 2, WIN_H - 40))

    def begin_quit(self):
        """退出游戏: 屏幕缓慢变暗后退出"""
        self.quitting = True
        self.settings.save()

    # ---------- 主循环 ----------

    def handle_event(self, event):
        self.music.handle_event(event)
        if self.quitting:
            return
        if event.type == pygame.QUIT:
            self.begin_quit()
            return
        if self.scene == 'menu':
            self.menu.handle_event(event)
        elif self.scene == 'settings':
            self.settings_screen.handle_event(event)
        elif self.scene == 'game':
            if not self.game.handle_event(event):
                self.game = None
                self.show_menu()

    def update(self, dt):
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.quitting:
            self.fade_alpha += dt * 170  # 约1.5秒完全变暗
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.running = False
            return
        if self.scene == 'game' and self.game:
            self.game.update(dt)

    def render(self):
        if self.scene == 'menu':
            self.menu.render(self.screen)
        elif self.scene == 'settings':
            self.settings_screen.render(self.screen)
        elif self.scene == 'game' and self.game:
            self.game.render(self.screen)

        if self.quitting:
            overlay = pygame.Surface((WIN_W, WIN_H))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(self.fade_alpha))
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def run(self):
        # 进入主界面后自动播放音乐
        if self.music.enabled:
            self.music.play()

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.render()

        self.music.shutdown()
        pygame.quit()


def main():
    app = App()
    app.run()


if __name__ == '__main__':
    main()
