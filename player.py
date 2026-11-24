"""
德州扑克 - 玩家与AI决策模块
Player and AI decision-making with different play styles (tightness/aggressiveness).
"""

import random
from cards import Card
from hand_evaluator import hand_strength_score, evaluate_best_hand, HAND_NAMES_ZH


class Player:
    """玩家基类"""

    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hole_cards = []
        self.current_bet = 0      # 当前下注轮已下注额
        self.total_bet = 0        # 本手总下注额
        self.is_folded = False
        self.is_all_in = False
        self.is_active = True
        self.last_action = None
        self.last_action_amount = 0
        self.position = None
        self.style_name = "Human"

    def reset_hand(self):
        """重置单手状态"""
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.is_folded = False
        self.is_all_in = False
        self.last_action = None
        self.last_action_amount = 0

    def reset_round(self):
        """重置每轮下注状态"""
        self.current_bet = 0
        self.last_action = None
        self.last_action_amount = 0

    def bet(self, amount):
        """下注，返回实际下注金额"""
        actual = min(amount, self.chips)
        self.chips -= actual
        self.current_bet += actual
        self.total_bet += actual
        if self.chips == 0:
            self.is_all_in = True
        return actual

    def __repr__(self):
        return f"{self.name}({self.style_name}, ${self.chips})"


# AI 性格预设: (tightness, aggressiveness, bluff_freq, name_zh)
AI_PROFILES = {
    'rock':     (0.80, 0.20, 0.04, '岩石'),
    'shark':    (0.70, 0.75, 0.12, '鲨鱼'),
    'station':  (0.30, 0.25, 0.05, '跟注站'),
    'maniac':   (0.25, 0.85, 0.28, '疯子'),
    'balanced': (0.55, 0.50, 0.10, '均衡型'),
    'nit':      (0.88, 0.15, 0.02, '超紧'),
}

# 位置对应中文
POSITION_NAMES_ZH = {
    'BTN': '庄家',
    'SB':  '小盲',
    'BB':  '大盲',
    'UTG': '枪口',
    'MP':  '中位',
    'CO':  '截击',
}


class HumanPlayer(Player):
    """人类玩家: 决策由界面层提供, 引擎侧与普通玩家一致"""

    def __init__(self, name, chips=1000):
        super().__init__(name, chips)
        self.style_name = "人类"

    def make_decision(self, game_state):
        """不应被引擎直接调用 (界面层负责收集输入)"""
        raise NotImplementedError("HumanPlayer 的决策由界面层处理")


class AIPlayer(Player):
    """
    AI 玩家: 根据手牌强度、底池赔率、性格参数自主决策。

    tightness   : 0-1, 越高越紧 (只打好牌)
    aggressiveness: 0-1, 越高越爱加注/下注
    bluff_freq  : 0-1, 诈唬频率
    """

    def __init__(self, name, profile_key, chips=1000, seed=None):
        super().__init__(name, chips)
        self.profile_key = profile_key
        self.tightness, self.aggressiveness, self.bluff_freq, self.style_name = AI_PROFILES[profile_key]
        self._rng = random.Random(seed)
        self.thinking = False  # GUI用于显示思考动画

    def make_decision(self, game_state):
        """
        根据游戏状态做出决策。

        game_state dict:
            - hole_cards: list[Card]
            - community: list[Card]
            - to_call: int (需要跟注的差额)
            - min_raise: int (最小加注额)
            - pot: int (当前底池)
            - round_name: str ('preflop'/'flop'/'turn'/'river')
            - position: str
            - active_players: int
            - big_blind: int
            - can_check: bool
        返回: (action_str, amount_int)
        action: 'fold' | 'check' | 'call' | 'bet' | 'raise' | 'all_in'
        """
        hole = game_state['hole_cards']
        community = game_state['community']
        to_call = game_state['to_call']
        min_raise = game_state['min_raise']
        pot = game_state['pot']
        round_name = game_state['round_name']
        position = game_state.get('position', 'MP')
        active_players = game_state['active_players']
        big_blind = game_state['big_blind']
        can_check = game_state.get('can_check', False)

        # 1. 评估手牌强度 (0-1)
        strength = hand_strength_score(hole, community)

        # 2. 位置调整: 后位更松
        position_adjust = self._position_adjust(position)
        effective_tightness = max(0.05, self.tightness - position_adjust)

        # 3. 翻前/翻后策略不同
        if round_name == 'preflop':
            decision = self._decide_preflop(
                strength, to_call, min_raise, pot, effective_tightness,
                can_check, big_blind, active_players
            )
        else:
            decision = self._decide_postflop(
                hole, community, strength, to_call, min_raise, pot,
                effective_tightness, can_check, big_blind, round_name, active_players
            )

        return decision

    def _position_adjust(self, position):
        """位置越靠后越松，返回松紧度减少量"""
        adjusts = {
            'UTG': 0.00, 'MP': 0.02, 'CO': 0.06,
            'BTN': 0.10, 'SB': 0.03, 'BB': 0.08,
        }
        return adjusts.get(position, 0.03)

    def _decide_preflop(self, strength, to_call, min_raise, pot,
                        tightness, can_check, big_blind, active_players):
        """翻前决策"""
        # 决策阈值
        fold_threshold = 0.15 + tightness * 0.25   # 0.15~0.40
        call_threshold = 0.25 + tightness * 0.20   # 0.25~0.45
        raise_threshold = 0.55 + tightness * 0.15  # 0.55~0.70

        # 可以过牌 (大盲位没人加注)
        if can_check:
            if strength > raise_threshold and self._rng.random() < self.aggressiveness:
                # 加注
                raise_amt = max(min_raise, int(big_blind * (2.5 + self._rng.random() * 1.5)))
                raise_amt = min(raise_amt, self.chips)
                return self._action('raise', raise_amt)
            elif strength > call_threshold * 0.7 and self._rng.random() < self.aggressiveness * 0.5:
                # 中等牌有时也小加注
                raise_amt = max(min_raise, int(big_blind * 2))
                raise_amt = min(raise_amt, self.chips)
                return self._action('raise', raise_amt)
            else:
                return self._action('check', 0)

        # 需要跟注
        if strength < fold_threshold:
            # 弱牌: 考虑诈唬或弃牌
            if self._rng.random() < self.bluff_freq and to_call <= big_blind * 3:
                bluff_raise = max(min_raise, int(big_blind * 3))
                bluff_raise = min(bluff_raise, self.chips)
                return self._action('raise', bluff_raise)
            return self._action('fold', 0)

        # 中等牌: 跟注或弃牌
        if strength < call_threshold:
            # 底池赔率
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0
            if strength > pot_odds * 0.9 or self._rng.random() < (1 - tightness) * 0.4:
                if to_call >= self.chips:
                    return self._action('all_in', self.chips)
                return self._action('call', to_call)
            else:
                return self._action('fold', 0)

        # 较强牌: 跟注或加注
        if strength < raise_threshold:
            if self._rng.random() < self.aggressiveness * 0.6:
                raise_amt = max(min_raise, int(to_call + big_blind * 2))
                raise_amt = min(raise_amt, self.chips)
                return self._action('raise', raise_amt)
            else:
                if to_call >= self.chips:
                    return self._action('all_in', self.chips)
                return self._action('call', to_call)

        # 强牌: 加注/全压
        if strength > raise_threshold + 0.15:
            # 很强, 可能全压
            if self._rng.random() < self.aggressiveness * 0.5 and self.chips < pot * 3:
                return self._action('all_in', self.chips)

        raise_amt = max(min_raise, int(to_call + big_blind * (2.5 + self._rng.random() * 2)))
        raise_amt = min(raise_amt, self.chips)
        return self._action('raise', raise_amt)

    def _decide_postflop(self, hole, community, strength, to_call, min_raise,
                        pot, tightness, can_check, big_blind, round_name, active_players):
        """翻后决策"""

        # 检测听牌 (同花听牌、顺子听牌)
        has_draw = self._detect_draws(hole, community)

        # 听牌加成
        if has_draw.get('flush_draw') or has_draw.get('straight_draw'):
            strength = min(1.0, strength + 0.15)

        # 决策阈值 (翻后比翻前更松一点)
        fold_threshold = 0.12 + tightness * 0.20
        call_threshold = 0.22 + tightness * 0.18
        raise_threshold = 0.55 + tightness * 0.12
        bet_threshold = 0.40 + tightness * 0.15

        # 可以过牌
        if can_check:
            if strength > raise_threshold and self._rng.random() < self.aggressiveness:
                # 强牌: 下注
                bet = max(big_blind, int(pot * (0.5 + self._rng.random() * 0.5)))
                bet = min(bet, self.chips)
                return self._action('bet', bet)
            elif strength > bet_threshold and self._rng.random() < self.aggressiveness * 0.7:
                # 中强牌: 小注
                bet = max(big_blind, int(pot * (0.33 + self._rng.random() * 0.3)))
                bet = min(bet, self.chips)
                return self._action('bet', bet)
            elif self._rng.random() < self.bluff_freq:
                # 诈唬下注
                bet = max(big_blind, int(pot * (0.4 + self._rng.random() * 0.4)))
                bet = min(bet, self.chips)
                return self._action('bet', bet)
            else:
                return self._action('check', 0)

        # 需要跟注
        # 底池赔率
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0

        if strength < fold_threshold:
            # 弱牌
            if self._rng.random() < self.bluff_freq and to_call <= pot * 0.3:
                # 诈唬加注
                raise_amt = max(min_raise, int(to_call + pot * 0.6))
                raise_amt = min(raise_amt, self.chips)
                return self._action('raise', raise_amt)
            # 有听牌时跟注
            if (has_draw.get('flush_draw') or has_draw.get('straight_draw')) and pot_odds < 0.25:
                if to_call >= self.chips:
                    return self._action('all_in', self.chips)
                return self._action('call', to_call)
            return self._action('fold', 0)

        if strength < call_threshold:
            # 中等偏弱: 看底池赔率
            if strength > pot_odds * 0.85 or (1 - tightness) > self._rng.random():
                if to_call >= self.chips:
                    return self._action('all_in', self.chips)
                return self._action('call', to_call)
            else:
                return self._action('fold', 0)

        if strength < raise_threshold:
            # 中等偏强: 跟注或偶尔加注
            if self._rng.random() < self.aggressiveness * 0.4:
                raise_amt = max(min_raise, int(to_call + pot * 0.5))
                raise_amt = min(raise_amt, self.chips)
                return self._action('raise', raise_amt)
            else:
                if to_call >= self.chips:
                    return self._action('all_in', self.chips)
                return self._action('call', to_call)

        # 强牌: 加注
        if strength > raise_threshold + 0.15 and self._rng.random() < self.aggressiveness * 0.6:
            # 很强, 可能全压
            if self.chips < pot * 2:
                return self._action('all_in', self.chips)

        raise_amt = max(min_raise, int(to_call + pot * (0.6 + self._rng.random() * 0.5)))
        raise_amt = min(raise_amt, self.chips)
        return self._action('raise', raise_amt)

    def _detect_draws(self, hole, community):
        """检测同花听牌和顺子听牌"""
        all_cards = hole + community
        result = {'flush_draw': False, 'straight_draw': False}

        # 同花听牌: 4张同花色
        suit_counts = {}
        for c in all_cards:
            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
        for suit, count in suit_counts.items():
            if count == 4:
                result['flush_draw'] = True
                break

        # 顺子听牌: 检测连续牌
        ranks = sorted(set(c.rank for c in all_cards))
        # 特殊处理A低位
        if 14 in ranks:
            ranks = [1] + ranks

        max_consecutive = 1
        current = 1
        for i in range(1, len(ranks)):
            if ranks[i] == ranks[i-1] + 1:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 1

        if max_consecutive >= 4:
            result['straight_draw'] = True

        return result

    def _action(self, action, amount):
        """生成动作元组"""
        self.last_action = action
        self.last_action_amount = amount
        return (action, amount)
