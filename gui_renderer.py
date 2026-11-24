"""
德州扑克 - Pygame 渲染器
Drawing functions for cards, table, players, chips, etc.
"""

import pygame
import math
from cards import Card, RANK_NAMES, SUIT_SYMBOLS, SUIT_COLORS
from player import POSITION_NAMES_ZH
from hand_evaluator import HAND_NAMES_ZH

# 字体缓存 (避免每帧重建)
_font_cache = {}

def _get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _font_cache[key]

# 颜色
BG_COLOR = (15, 35, 25)
TABLE_COLOR = (10, 80, 40)
TABLE_BORDER = (180, 150, 60)
FELT_COLOR = (12, 100, 55)
CARD_BG = (252, 250, 245)
CARD_BORDER = (40, 40, 40)
TEXT_WHITE = (240, 240, 240)
TEXT_GOLD = (220, 180, 80)
TEXT_RED = (220, 60, 60)
TEXT_GREEN = (80, 200, 80)
TEXT_GRAY = (160, 160, 160)
PANEL_BG = (20, 45, 30)
ACTION_COLORS = {
    'fold': (180, 50, 50),
    'check': (100, 100, 220),
    'call': (80, 180, 80),
    'bet': (220, 160, 40),
    'raise': (220, 100, 40),
    'all_in': (200, 40, 200),
}
DEALER_BTN_COLOR = (255, 255, 255)

# 卡牌尺寸
CARD_W = 50
CARD_H = 70

# 玩家信息卡片尺寸
SEAT_W = 160
SEAT_H = 95


def init_fonts():
    """初始化字体"""
    font_name = "microsoftyahei,simhei,arial"
    return {
        'large': pygame.font.SysFont(font_name, 28, bold=True),
        'medium': pygame.font.SysFont(font_name, 20, bold=True),
        'small': pygame.font.SysFont(font_name, 16),
        'tiny': pygame.font.SysFont(font_name, 13),
        'big': pygame.font.SysFont(font_name, 36, bold=True),
    }


def draw_card(surface, card, x, y, face_up=True, scale=1.0):
    """
    绘制一张扑克牌。
    card: Card对象或None (绘制牌背)
    """
    w = int(CARD_W * scale)
    h = int(CARD_H * scale)

    if card is None or not face_up:
        # 牌背
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, (60, 100, 180), rect, border_radius=5)
        pygame.draw.rect(surface, (30, 50, 120), rect, 2, border_radius=5)
        # 图案
        inner = pygame.Rect(x + 4, y + 4, w - 8, h - 8)
        pygame.draw.rect(surface, (40, 80, 160), inner, border_radius=3)
        return

    # 牌面
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, CARD_BG, rect, border_radius=5)
    pygame.draw.rect(surface, CARD_BORDER, rect, 2, border_radius=5)

    suit = card.suit
    rank = RANK_NAMES[card.rank]
    color = (200, 30, 30) if SUIT_COLORS[suit] == 'red' else (20, 20, 20)

    # 左上角点数+花色
    font = _get_font(int(16 * scale), bold=True)
    rank_surf = font.render(rank, True, color)
    surface.blit(rank_surf, (x + 3, y + 2))

    suit_font = _get_font(int(14 * scale))
    suit_surf = suit_font.render(SUIT_SYMBOLS[suit], True, color)
    surface.blit(suit_surf, (x + 3, y + 18 * scale))

    # 中心大花色
    big_font = _get_font(int(26 * scale))
    big_suit = big_font.render(SUIT_SYMBOLS[suit], True, color)
    bw = big_suit.get_width()
    surface.blit(big_suit, (x + (w - bw) // 2, y + h // 2 - int(14 * scale)))

    # 右下角倒置点数
    if len(rank) == 1:
        br_rank = pygame.transform.rotate(rank_surf, 180)
        surface.blit(br_rank, (x + w - br_rank.get_width() - 3, y + h - br_rank.get_height() - 2))


def draw_table(surface, center_x, center_y, rx, ry):
    """绘制桌面"""
    # 外阴影
    shadow_rect = pygame.Rect(center_x - rx - 5, center_y - ry - 5, (rx + 5) * 2, (ry + 5) * 2)
    pygame.draw.ellipse(surface, (5, 25, 15), shadow_rect)

    # 桌面外圈
    outer_rect = pygame.Rect(center_x - rx, center_y - ry, rx * 2, ry * 2)
    pygame.draw.ellipse(surface, TABLE_COLOR, outer_rect)

    # 金色边框
    pygame.draw.ellipse(surface, TABLE_BORDER, outer_rect, 4)

    # 内圈桌面 (毛毡)
    inner_rx = int(rx * 0.88)
    inner_ry = int(ry * 0.88)
    inner_rect = pygame.Rect(center_x - inner_rx, center_y - inner_ry, inner_rx * 2, inner_ry * 2)
    pygame.draw.ellipse(surface, FELT_COLOR, inner_rect)
    pygame.draw.ellipse(surface, (5, 60, 30), inner_rect, 2)


def draw_seat(surface, player, x, y, is_current, is_dealer, fonts, show_cards=True, face_up_cards=True):
    """
    绘制玩家座位信息。
    x, y: 座位左上角坐标
    face_up_cards: 是否明牌显示该玩家底牌 (参与模式对对手传False)
    """
    # 背景面板
    panel = pygame.Rect(x, y, SEAT_W, SEAT_H)
    bg_color = (40, 80, 50) if is_current else (25, 50, 35)
    pygame.draw.rect(surface, bg_color, panel, border_radius=8)
    border_color = TEXT_GOLD if is_current else (60, 100, 70)
    pygame.draw.rect(surface, border_color, panel, 2, border_radius=8)

    # 玩家名
    name_color = TEXT_GOLD if is_current else TEXT_WHITE
    name_surf = fonts['medium'].render(player.name, True, name_color)
    surface.blit(name_surf, (x + 8, y + 4))

    # 风格名
    style_surf = fonts['tiny'].render(f"[{player.style_name}]", True, TEXT_GRAY)
    surface.blit(style_surf, (x + 8, y + 26))

    # 位置
    pos_text = ""
    if player.position:
        pos_text = POSITION_NAMES_ZH.get(player.position, player.position)
    pos_surf = fonts['tiny'].render(f"位置: {pos_text}", True, TEXT_GRAY)
    surface.blit(pos_surf, (x + 8, y + 40))

    # 筹码
    chip_text = f"${player.chips}"
    chip_surf = fonts['medium'].render(chip_text, True, TEXT_GREEN)
    surface.blit(chip_surf, (x + 8, y + 54))

    # 当前下注
    if player.current_bet > 0:
        bet_text = f"下注: ${player.current_bet}"
        bet_surf = fonts['small'].render(bet_text, True, TEXT_GOLD)
        surface.blit(bet_surf, (x + 8, y + 76))

    # 弃牌标记
    if player.is_folded:
        fold_surf = fonts['big'].render("FOLD", True, (100, 100, 100))
        fw = fold_surf.get_width()
        surface.blit(fold_surf, (x + SEAT_W // 2 - fw // 2, y + SEAT_H // 2 - 18))

    # 全压标记
    if player.is_all_in:
        ai_surf = fonts['medium'].render("ALL IN", True, (220, 40, 200))
        surface.blit(ai_surf, (x + SEAT_W - 65, y + 4))

    # 庄家按钮
    if is_dealer:
        btn_x = x + SEAT_W - 20
        btn_y = y + SEAT_H - 20
        pygame.draw.circle(surface, DEALER_BTN_COLOR, (btn_x, btn_y), 12)
        pygame.draw.circle(surface, (40, 40, 40), (btn_x, btn_y), 12, 2)
        d_surf = fonts['tiny'].render("D", True, (40, 40, 40))
        surface.blit(d_surf, (btn_x - 4, btn_y - 6))

    # 底牌
    if show_cards and player.hole_cards and not player.is_folded:
        card_y = y - CARD_H - 5
        for i, card in enumerate(player.hole_cards):
            draw_card(surface, card, x + 10 + i * (CARD_W + 4), card_y, face_up=face_up_cards)
    elif show_cards and player.is_folded:
        # 显示弃牌 (牌背)
        card_y = y - CARD_H - 5
        for i in range(len(player.hole_cards)):
            draw_card(surface, None, x + 10 + i * (CARD_W + 4), card_y, face_up=False)

    # 动作标签
    if player.last_action and not player.is_folded:
        act_color = ACTION_COLORS.get(player.last_action, TEXT_WHITE)
        act_text = {
            'fold': '弃牌', 'check': '过牌', 'call': '跟注',
            'bet': '下注', 'raise': '加注', 'all_in': '全压',
        }.get(player.last_action, player.last_action)
        if player.last_action_amount > 0:
            act_text += f" ${player.last_action_amount}"
        act_surf = fonts['small'].render(act_text, True, act_color)
        aw = act_surf.get_width()
        # 在座位上方显示
        surface.blit(act_surf, (x + SEAT_W // 2 - aw // 2, y - 40))


def draw_community(surface, cards, center_x, center_y, fonts):
    """绘制公共牌"""
    if not cards:
        hint = fonts['small'].render("等待公共牌...", True, TEXT_GRAY)
        hw = hint.get_width()
        surface.blit(hint, (center_x - hw // 2, center_y - CARD_H // 2))
        return

    total_w = len(cards) * (CARD_W + 6) - 6
    start_x = center_x - total_w // 2
    for i, card in enumerate(cards):
        draw_card(surface, card, start_x + i * (CARD_W + 6), center_y - CARD_H // 2)


def draw_pot(surface, pot, center_x, center_y, fonts):
    """绘制底池"""
    text = f"底池: ${pot}"
    surf = fonts['large'].render(text, True, TEXT_GOLD)
    w = surf.get_width()
    # 底池在公共牌下方
    surface.blit(surf, (center_x - w // 2, center_y + CARD_H // 2 + 10))


def draw_round_indicator(surface, round_name, x, y, fonts):
    """绘制当前轮次"""
    names = {
        'preflop': '翻前', 'flop': '翻牌', 'turn': '转牌',
        'river': '河牌', 'showdown': '摊牌', 'idle': '等待', 'game_over': '游戏结束',
    }
    text = names.get(round_name, round_name)
    surf = fonts['large'].render(text, True, TEXT_WHITE)
    pygame.draw.rect(surface, PANEL_BG, (x - 10, y - 5, surf.get_width() + 20, surf.get_height() + 10), border_radius=5)
    pygame.draw.rect(surface, TEXT_GOLD, (x - 10, y - 5, surf.get_width() + 20, surf.get_height() + 10), 2, border_radius=5)
    surface.blit(surf, (x, y))


def draw_log_panel(surface, log, x, y, w, h, fonts):
    """绘制游戏日志"""
    panel = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, PANEL_BG, panel, border_radius=5)
    pygame.draw.rect(surface, (50, 80, 60), panel, 2, border_radius=5)

    title = fonts['small'].render("游戏日志", True, TEXT_GOLD)
    surface.blit(title, (x + 8, y + 4))

    # 显示最后几条
    lines = log[-(h // 18):] if log else []
    for i, line in enumerate(lines):
        line_surf = fonts['tiny'].render(line[:50], True, TEXT_GRAY)
        surface.blit(line_surf, (x + 8, y + 24 + i * 18))


def draw_winners(surface, winners, center_x, center_y, fonts):
    """绘制赢家信息"""
    if not winners:
        return
    y = center_y + 60
    for i, (winner, amount, hand_type) in enumerate(winners):
        text = f"  {winner.name} 赢得 ${amount}  "
        if hand_type and hand_type != 'uncontested':
            ht = HAND_NAMES_ZH.get(hand_type, hand_type)
            text += f"({ht})"
        surf = fonts['medium'].render(text, True, TEXT_GOLD)
        w = surf.get_width()
        bg = pygame.Rect(center_x - w // 2 - 5, y + i * 28 - 3, w + 10, surf.get_height() + 6)
        pygame.draw.rect(surface, (30, 60, 40), bg, border_radius=4)
        surface.blit(surf, (center_x - w // 2, y + i * 28))


def draw_controls_hint(surface, fonts):
    """绘制控制提示"""
    hints = [
        "空格: 暂停/继续",
        "N: 下一手",
        "+/-: 调速",
        "ESC: 退出",
    ]
    y = surface.get_height() - 80
    for i, h in enumerate(hints):
        surf = fonts['tiny'].render(h, True, TEXT_GRAY)
        surface.blit(surf, (10, y + i * 16))


def draw_speed_indicator(surface, speed, fonts):
    """绘制速度"""
    text = f"速度: {speed:.1f}x"
    surf = fonts['small'].render(text, True, TEXT_GRAY)
    surface.blit(surf, (surface.get_width() - 120, surface.get_height() - 25))
