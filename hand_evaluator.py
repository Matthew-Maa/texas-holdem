"""
德州扑克 - 牌型评估模块
Evaluate the best 5-card hand from 7 cards (2 hole + 5 community).
"""

from itertools import combinations
from cards import Card

# 牌型等级 (越大越强)
HAND_RANKS = {
    'high_card':       0,
    'one_pair':        1,
    'two_pair':        2,
    'three_of_a_kind': 3,
    'straight':        4,
    'flush':           5,
    'full_house':      6,
    'four_of_a_kind':  7,
    'straight_flush':  8,
    'royal_flush':     9,
}

HAND_NAMES_ZH = {
    'high_card':       '高牌',
    'one_pair':        '一对',
    'two_pair':        '两对',
    'three_of_a_kind': '三条',
    'straight':        '顺子',
    'flush':           '同花',
    'full_house':      '葫芦',
    'four_of_a_kind':  '四条',
    'straight_flush':  '同花顺',
    'royal_flush':     '皇家同花顺',
}


def _evaluate_five(cards):
    """
    评估5张牌的牌型，返回 (rank_value, tiebreaker_tuple, hand_name)。
    cards: list of 5 Card objects.
    """
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    is_flush = len(set(suits)) == 1

    # 检查顺子 (含 A-2-3-4-5 特殊情况)
    is_straight = False
    straight_high = None
    unique_ranks = sorted(set(ranks), reverse=True)
    if len(unique_ranks) == 5:
        if unique_ranks[0] - unique_ranks[4] == 4:
            is_straight = True
            straight_high = unique_ranks[0]
        # A-2-3-4-5 (轮子)
        elif set(unique_ranks) == {14, 5, 4, 3, 2}:
            is_straight = True
            straight_high = 5  # 5为最高

    # 统计每个点数出现次数
    from collections import Counter
    rank_counts = Counter(ranks)
    # 按出现次数降序，同次数按点数降序
    counts_sorted = sorted(rank_counts.items(), key=lambda x: (-x[1], -x[0]))

    counts = [c for _, c in counts_sorted]
    sorted_ranks_by_count = [r for r, _ in counts_sorted]

    # 四条
    if counts == [4, 1]:
        cat = 'four_of_a_kind'
        tb = tuple(sorted_ranks_by_count)
    # 葫芦
    elif counts == [3, 2]:
        cat = 'full_house'
        tb = tuple(sorted_ranks_by_count)
    # 同花顺 / 皇家同花顺
    elif is_straight and is_flush:
        if straight_high == 14:
            cat = 'royal_flush'
            tb = (14,)
        else:
            cat = 'straight_flush'
            tb = (straight_high,)
    # 同花
    elif is_flush:
        cat = 'flush'
        tb = tuple(ranks)
    # 顺子
    elif is_straight:
        cat = 'straight'
        tb = (straight_high,)
    # 三条
    elif counts == [3, 1, 1]:
        cat = 'three_of_a_kind'
        tb = tuple(sorted_ranks_by_count)
    # 两对
    elif counts == [2, 2, 1]:
        cat = 'two_pair'
        tb = tuple(sorted_ranks_by_count)
    # 一对
    elif counts == [2, 1, 1, 1]:
        cat = 'one_pair'
        tb = tuple(sorted_ranks_by_count)
    # 高牌
    else:
        cat = 'high_card'
        tb = tuple(ranks)

    return (HAND_RANKS[cat], tb, cat)


def evaluate_best_hand(cards):
    """
    从给定的卡牌中选出最佳5张牌组合。
    cards: list of Card objects (5-7张).
    返回: (rank_value, tiebreaker_tuple, hand_name, best_five_cards)
    """
    if len(cards) < 5:
        raise ValueError(f"至少需要5张牌，当前{len(cards)}张")

    best = None
    best_cards = None

    for combo in combinations(cards, 5):
        result = _evaluate_five(list(combo))
        if best is None or result[:2] > best[:2]:
            best = result
            best_cards = combo

    return (*best, best_cards)


def compare_hands(h1, h2):
    """
    比较两手牌的强度。
    h1, h2: evaluate_best_hand 的返回结果。
    返回: 1 if h1 > h2, -1 if h1 < h2, 0 if tie.
    """
    if h1[:2] > h2[:2]:
        return 1
    elif h1[:2] < h2[:2]:
        return -1
    else:
        return 0


def hand_strength_score(cards, community=None):
    """
    返回0-1之间的手牌强度分数，用于AI决策。
    cards: 玩家手牌 (2张).
    community: 公共牌 (0-5张).
    """
    if community is None:
        community = []

    all_cards = cards + community
    if len(all_cards) >= 5:
        result = evaluate_best_hand(all_cards)
        # 将牌型等级映射到0-1: royal_flush=9 -> ~1.0, high_card=0 -> ~0.1
        rank_val = result[0]
        # 加上tiebreaker的影响
        tb = result[1]
        tb_score = 0.0
        if tb:
            # 归一化tiebreaker (最大14)
            tb_score = sum(t / 14.0 for t in tb) / len(tb) * 0.1
        score = rank_val / 9.0 * 0.9 + tb_score
        return min(1.0, score)
    else:
        # 只有两张底牌时，用简化评估
        return _preflop_strength(cards)


def _preflop_strength(hole_cards):
    """
    翻前两张底牌的简化强度评估 (0-1)。
    """
    r1, r2 = hole_cards[0].rank, hole_cards[1].rank
    suited = hole_cards[0].suit == hole_cards[1].suit
    high = max(r1, r2)
    low = min(r1, r2)

    # 对子
    if r1 == r2:
        # AA=1.0, KK=0.92, ... 22=0.45
        return 0.45 + (r1 - 2) / 12.0 * 0.55

    # 非对子
    # 基础分: 高牌越高越好
    base = (high - 2) / 12.0 * 0.4 + (low - 2) / 12.0 * 0.15

    # 同花加成
    if suited:
        base += 0.1

    # 连张加成 (gap越小越好)
    gap = high - low - 1
    if gap == 0:  # 连张
        base += 0.08
    elif gap == 1:  # 一隔
        base += 0.04

    # 大牌加成 (A高)
    if high == 14:
        base += 0.05
        if low >= 10:  # AK, AQ, AJ, AT
            base += 0.05

    return min(0.85, base)
