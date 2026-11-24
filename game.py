"""
德州扑克 - 游戏引擎模块
Texas Hold'em game engine: betting rounds, pot management, showdown.
"""

import random
from cards import Deck, Card
from player import Player, AIPlayer, AI_PROFILES, POSITION_NAMES_ZH
from hand_evaluator import evaluate_best_hand, compare_hands, HAND_NAMES_ZH


class PokerGame:
    """
    德州扑克游戏引擎。

    状态流转:
        idle -> preflop -> flop -> turn -> river -> showdown -> idle
    """

    # 6人桌位置顺序 (从庄家开始顺时针)
    POSITIONS_6 = ['SB', 'BB', 'UTG', 'MP', 'CO', 'BTN']

    def __init__(self, players, small_blind=10, big_blind=20, seed=None):
        self.players = players
        self.num_players = len(players)
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = Deck(seed)
        self._rng = random.Random(seed)

        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.min_raise = big_blind
        self.dealer_idx = 0
        self.round_name = 'idle'
        self.hand_num = 0

        # 每轮追踪
        self.players_to_act = []       # 还需行动的玩家索引
        self.last_raiser_idx = -1      # 最后加注者
        self.winners = []
        self.side_pots = []
        self.log = []                  # 事件日志

    def _log(self, msg):
        """记录游戏事件"""
        self.log.append(msg)

    def start_new_hand(self):
        """开始新一手牌"""
        self.hand_num += 1
        self.deck.reset()
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.winners = []
        self.side_pots = []
        self.log = []

        # 重置所有玩家
        for p in self.players:
            p.reset_hand()

        # 移除没筹码的玩家
        active = [p for p in self.players if p.chips > 0]
        if len(active) < 2:
            self.round_name = 'game_over'
            self._log("游戏结束!")
            return

        # 移动庄家位
        self.dealer_idx = self._next_active_idx(self.dealer_idx)

        # 分配位置
        self._assign_positions()

        # 发底牌 (仅发给本手有筹码的玩家)
        for _ in range(2):
            for i in range(self.num_players):
                if self.players[i].chips > 0:
                    self.players[i].hole_cards.append(self.deck.deal())

        # 下盲注
        self._post_blinds()

        # 开始翻前下注轮 (当前注 = 实际落下的最大盲注, 短筹码大盲可能不足额)
        self.round_name = 'preflop'
        self.current_bet = max(p.total_bet for p in self.players)
        self.min_raise = self.big_blind

        # 翻前第一个行动者: 大盲后第一个
        first = self._next_active_after(self._bb_idx())
        self._init_betting_round(first)

        self._log(f"--- 第 {self.hand_num} 手开始 ---")
        self._log(f"庄家: {self.players[self.dealer_idx].name}")

    def _next_active_idx(self, from_idx):
        """从 from_idx 顺时针找下一个有筹码的玩家"""
        idx = (from_idx + 1) % self.num_players
        while idx != from_idx:
            if self.players[idx].chips > 0:
                return idx
            idx = (idx + 1) % self.num_players
        return from_idx

    def _next_active_after(self, idx):
        """从 idx 之后找下一个未弃牌且未全压的活跃玩家"""
        next_idx = (idx + 1) % self.num_players
        for _ in range(self.num_players):
            p = self.players[next_idx]
            if not p.is_folded and not p.is_all_in and p.chips >= 0:
                # 有筹码或已下注的都算可行动
                if p.chips > 0 or p.current_bet < self.current_bet:
                    return next_idx
            next_idx = (next_idx + 1) % self.num_players
        return -1

    def _assign_positions(self):
        """分配桌面位置"""
        positions = self.POSITIONS_6[:self.num_players]
        # 从庄家开始逆时针分配 (庄家是BTN)
        # 但我们按顺时针, SB在dealer后
        idx = self.dealer_idx
        # 单挑时: 庄家为 BTN(兼小盲), 另一人为 BB
        pos_order = ['BTN', 'BB'] if self.num_players == 2 else ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
        for i in range(self.num_players):
            p = self.players[idx]
            if p.chips > 0:
                p.position = pos_order[i % len(pos_order)]
            else:
                p.position = None
            idx = (idx + 1) % self.num_players

    def _sb_idx(self):
        """小盲位 (单挑时庄家兼小盲)"""
        active_n = sum(1 for p in self.players if p.chips > 0)
        if active_n == 2:
            return self.dealer_idx
        return self._next_active_idx(self.dealer_idx)

    def _bb_idx(self):
        """大盲位"""
        return self._next_active_idx(self._sb_idx())

    def _post_blinds(self):
        """下盲注"""
        sb_idx = self._sb_idx()
        bb_idx = self._bb_idx()

        sb_player = self.players[sb_idx]
        sb_amt = sb_player.bet(self.small_blind)
        self.pot += sb_amt
        self._log(f"{sb_player.name} 下小盲 {sb_amt}")

        bb_player = self.players[bb_idx]
        bb_amt = bb_player.bet(self.big_blind)
        self.pot += bb_amt
        self._log(f"{bb_player.name} 下大盲 {bb_amt}")

    def _init_betting_round(self, first_idx):
        """初始化一个下注轮"""
        self.players_to_act = []
        if first_idx < 0:
            return

        # 所有人重置本轮状态
        for p in self.players:
            p.reset_round()

        # 翻后大盲位已有注, 需保留
        if self.round_name == 'preflop':
            # 盲注已下, 恢复
            sb = self.players[self._sb_idx()]
            bb = self.players[self._bb_idx()]
            sb.current_bet = sb.total_bet
            bb.current_bet = bb.total_bet

        # 加入所有可行动玩家 (必须有筹码)
        idx = first_idx
        for _ in range(self.num_players):
            p = self.players[idx]
            if not p.is_folded and not p.is_all_in and p.chips > 0:
                self.players_to_act.append(idx)
            idx = (idx + 1) % self.num_players

        self.last_raiser_idx = -1

    def get_player_to_act(self):
        """获取当前需要行动的玩家, 返回 (idx, player) 或 None"""
        if not self.players_to_act:
            return None
        idx = self.players_to_act[0]
        return (idx, self.players[idx])

    def get_game_state_for(self, player_idx):
        """构建给AI决策用的游戏状态"""
        player = self.players[player_idx]
        to_call = self.current_bet - player.current_bet
        return {
            'hole_cards': player.hole_cards,
            'community': self.community,
            'to_call': max(0, to_call),
            'min_raise': self.min_raise,
            'pot': self.pot,
            'round_name': self.round_name,
            'position': player.position,
            'active_players': sum(1 for p in self.players if not p.is_folded),
            'big_blind': self.big_blind,
            'can_check': to_call <= 0,
        }

    def apply_action(self, player_idx, action, amount=0):
        """
        应用玩家动作, 推进游戏状态。
        action: 'fold' | 'check' | 'call' | 'bet' | 'raise' | 'all_in'
        """
        player = self.players[player_idx]
        to_call = self.current_bet - player.current_bet

        # 从行动队列移除当前玩家
        if player_idx in self.players_to_act:
            self.players_to_act.remove(player_idx)

        if action == 'fold':
            player.is_folded = True
            player.last_action = 'fold'
            self._log(f"{player.name} 弃牌")

        elif action == 'check':
            player.last_action = 'check'
            self._log(f"{player.name} 过牌")

        elif action == 'call':
            call_amt = min(to_call, player.chips)
            actual = player.bet(call_amt)
            self.pot += actual
            player.last_action = 'call'
            player.last_action_amount = actual
            if player.is_all_in:
                self._log(f"{player.name} 跟注全压 {actual}")
            else:
                self._log(f"{player.name} 跟注 {actual}")

        elif action == 'bet':
            actual = player.bet(amount)
            self.pot += actual
            self.current_bet = player.current_bet
            self.min_raise = max(self.big_blind, actual)
            player.last_action = 'bet'
            player.last_action_amount = actual
            self.last_raiser_idx = player_idx
            self._add_others_to_act(player_idx)
            self._log(f"{player.name} 下注 {actual}")

        elif action == 'raise':
            actual = player.bet(amount)
            self.pot += actual
            raise_size = actual - max(0, to_call)
            if player.current_bet > self.current_bet:
                # 只有真的把注码抬高才更新当前注/最小加注
                self.current_bet = player.current_bet
                if raise_size > 0:
                    self.min_raise = max(self.min_raise, raise_size)
                self.last_raiser_idx = player_idx
                self._add_others_to_act(player_idx)
            player.last_action = 'raise'
            player.last_action_amount = actual
            if player.is_all_in:
                self._log(f"{player.name} 加注全压到 {self.current_bet}")
            else:
                self._log(f"{player.name} 加注到 {self.current_bet}")

        elif action == 'all_in':
            actual = player.bet(player.chips)
            self.pot += actual
            player.last_action = 'all_in'
            player.last_action_amount = actual
            if player.current_bet > self.current_bet:
                raise_size = actual - max(0, to_call)
                self.current_bet = player.current_bet
                if raise_size > 0:
                    self.min_raise = max(self.min_raise, raise_size)
                self.last_raiser_idx = player_idx
                self._add_others_to_act(player_idx)
            self._log(f"{player.name} 全压 {actual}")

        # 检查是否只剩一人
        active = [p for p in self.players if not p.is_folded]
        if len(active) <= 1:
            self._end_hand_early()
            return

    def _add_others_to_act(self, raiser_idx):
        """加注后, 所有其他活跃且未全压的玩家需要重新行动"""
        new_queue = []
        idx = (raiser_idx + 1) % self.num_players
        for _ in range(self.num_players):
            p = self.players[idx]
            if idx != raiser_idx and not p.is_folded and not p.is_all_in and p.chips > 0:
                if idx not in new_queue:
                    new_queue.append(idx)
            idx = (idx + 1) % self.num_players
        self.players_to_act = new_queue

    def is_betting_round_complete(self):
        """当前下注轮是否结束"""
        if not self.players_to_act:
            return True
        return False

    def advance_round(self):
        """进入下一个下注轮或摊牌"""
        # 检查是否只剩一人 (已在apply_action中处理, 但双重保险)
        active = [p for p in self.players if not p.is_folded]
        if len(active) <= 1:
            self._end_hand_early()
            return

        # 全压检查: 如果所有活跃玩家都全压了, 直接发完公共牌
        all_in = all(p.is_all_in for p in active)

        if self.round_name == 'preflop':
            # 发翻牌
            self.deck.deal()  # 烧牌
            self.community = [self.deck.deal(), self.deck.deal(), self.deck.deal()]
            self.round_name = 'flop'
            self._log(f"翻牌: {' '.join(c.name for c in self.community)}")
        elif self.round_name == 'flop':
            self.deck.deal()
            self.community.append(self.deck.deal())
            self.round_name = 'turn'
            self._log(f"转牌: {self.community[-1].name}")
        elif self.round_name == 'turn':
            self.deck.deal()
            self.community.append(self.deck.deal())
            self.round_name = 'river'
            self._log(f"河牌: {self.community[-1].name}")
        elif self.round_name == 'river':
            self.showdown()
            return

        if all_in:
            # 全压后自动进入下一轮
            self.advance_round()
            return

        # 新下注轮: 从大盲位后第一个活跃玩家开始 (标准规则)
        self.current_bet = 0
        self.min_raise = self.big_blind
        first = self._next_active_after(self._bb_idx())
        self._init_betting_round(first)

    def _end_hand_early(self):
        """所有人弃牌只剩一人, 直接结束"""
        active = [p for p in self.players if not p.is_folded]
        if len(active) == 1:
            winner = active[0]
            winner.chips += self.pot
            self.winners = [(winner, self.pot, 'uncontested')]
            self._log(f"{winner.name} 赢得底池 {self.pot} (对手弃牌)")
            self.round_name = 'showdown'
        else:
            self.round_name = 'showdown'

    def showdown(self):
        """摊牌: 评估所有未弃牌玩家的牌"""
        self.round_name = 'showdown'
        active = [p for p in self.players if not p.is_folded]

        self._log("--- 摊牌 ---")

        # 计算边池
        pots = self._calculate_pots(active)

        all_winners = []
        for pot_info in pots:
            pot_amount = pot_info['amount']
            eligible = pot_info['eligible']
            if len(eligible) == 1:
                w = eligible[0]
                w.chips += pot_amount
                all_winners.append((w, pot_amount, 'uncontested'))
                self._log(f"{w.name} 赢得底池 {pot_amount}")
            else:
                # 评估每个人的牌
                best = None
                best_eval = None
                evaluations = {}
                for p in eligible:
                    all_cards = p.hole_cards + self.community
                    ev = evaluate_best_hand(all_cards)
                    evaluations[p] = ev
                    self._log(f"  {p.name}: {ev[2]} ({' '.join(c.name for c in ev[3])})")
                    if best_eval is None or compare_hands(ev, best_eval) > 0:
                        best_eval = ev
                        best = p

                # 检查平局
                tied = [p for p in eligible if compare_hands(evaluations[p], best_eval) == 0]
                share = pot_amount // len(tied)
                remainder = pot_amount - share * len(tied)
                for i, w in enumerate(tied):
                    won = share + (remainder if i == 0 else 0)
                    w.chips += won
                    all_winners.append((w, won, evaluations[w][2]))
                    self._log(f"  {w.name} 以 {HAND_NAMES_ZH[evaluations[w][2]]} 赢得 {won}")

        self.winners = all_winners

    def _calculate_pots(self, active):
        """
        计算主池和边池。
        返回 list of {'amount': int, 'eligible': [Player]}
        """
        if not active:
            return []

        # 所有有投入的玩家
        contributors = [(p, p.total_bet) for p in self.players if p.total_bet > 0]
        if not contributors:
            return [{'amount': self.pot, 'eligible': active}]

        # 按 total_bet 升序排列
        contributors.sort(key=lambda x: x[1])

        pots = []
        prev_level = 0
        remaining = list(contributors)

        while remaining:
            min_bet = remaining[0][1]
            level_amount = min_bet - prev_level

            # 所有至少投入 prev_level 的玩家贡献 level_amount 到这个池
            pot_amount = 0
            eligible = []
            for p, tb in contributors:
                if tb >= min_bet:
                    pot_amount += level_amount
                if tb >= min_bet and not p.is_folded:
                    eligible.append(p)

            if pot_amount > 0:
                pots.append({'amount': pot_amount, 'eligible': eligible[:]})

            # 移除已处理完的
            prev_level = min_bet
            remaining = [(p, tb) for p, tb in remaining if tb > min_bet]

        # 合并空池; 无人有资格的池 (该层级投入者全部弃牌) 滚入下一个有资格的池
        result = []
        carry = 0
        for p in pots:
            amt = p['amount'] + carry
            if p['eligible']:
                result.append({'amount': amt, 'eligible': p['eligible']})
                carry = 0
            else:
                carry = amt
        if carry and result:
            result[0]['amount'] += carry  # 兜底: 并回主池

        return result if result else [{'amount': self.pot, 'eligible': active}]

    def is_hand_complete(self):
        """当前手牌是否结束"""
        return self.round_name in ('showdown', 'game_over', 'idle')

    def get_results(self):
        """获取当前手牌结果"""
        return {
            'winners': self.winners,
            'pot': self.pot,
            'community': self.community,
            'log': self.log,
        }
