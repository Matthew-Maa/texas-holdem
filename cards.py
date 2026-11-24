"""
德州扑克 - 卡牌模块
Card and Deck classes for Texas Hold'em.
"""

import random

# 花色定义
SUITS = ['spades', 'hearts', 'diamonds', 'clubs']
SUIT_SYMBOLS = {
    'spades': '\u2660',
    'hearts': '\u2665',
    'diamonds': '\u2666',
    'clubs': '\u2663',
}
SUIT_COLORS = {
    'spades': 'black',
    'hearts': 'red',
    'diamonds': 'red',
    'clubs': 'black',
}

# 点数定义 (2-14, 14=A)
RANKS = list(range(2, 15))
RANK_NAMES = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
    8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
}


class Card:
    """单张扑克牌"""

    __slots__ = ('suit', 'rank')

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    @property
    def name(self):
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))


class Deck:
    """一副52张牌"""

    def __init__(self, seed=None):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        self._rng = random.Random(seed)
        self.shuffle()

    def shuffle(self):
        self._rng.shuffle(self.cards)

    def deal(self):
        """发一张牌"""
        if len(self.cards) == 0:
            raise RuntimeError("牌已发完")
        return self.cards.pop()

    def reset(self):
        """重置牌组"""
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        self.shuffle()

    def __len__(self):
        return len(self.cards)
