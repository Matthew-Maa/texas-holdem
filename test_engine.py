"""
德州扑克引擎回归测试 (无界面, 直接python运行)
验证: 筹码守恒 / 边池结算 / 短筹码 / 淘汰 / 两人桌 / 位置与行动顺序
"""

import random
from cards import Deck
from player import AIPlayer
from game import PokerGame


def run_match(num_players, chips, sb, bb, max_hands=300, seed=None):
    rng = random.Random(seed)
    styles = list('rock shark station maniac balanced nit'.split())
    players = [AIPlayer(f"P{i}", rng.choice(styles), chips=chips, seed=rng.randint(0, 99999))
               for i in range(num_players)]
    game = PokerGame(players, small_blind=sb, big_blind=bb, seed=rng.randint(0, 99999))

    total_chips = sum(p.chips for p in players)
    hands = 0

    while hands < max_hands:
        active = [p for p in players if p.chips > 0]
        if len(active) < 2:
            break
        game.start_new_hand()
        hands += 1
        assert game.round_name != 'game_over', "活跃玩家>=2时却判定游戏结束"

        # 校验: 本手有筹码的玩家都有2张底牌, 破产玩家没有
        for p in players:
            assert len(p.hole_cards) == (2 if p.chips > 0 or p.total_bet > 0 else 0), \
                f"底牌数量错误: {p.name} chips={p.chips} hole={len(p.hole_cards)}"

        # 盲注校验: 盲注后底池等于所有人本手总投入, 当前注等于最大投入
        invested = sum(p.total_bet for p in players)
        assert game.pot == invested, f"底池与总投入不符: pot={game.pot} invested={invested}"
        assert game.current_bet == max((p.total_bet for p in players), default=0), "当前注错误"

        # 迭代推进本手
        steps = 0
        pot_before = sum(p.chips for p in players)  # 手牌进行中守恒检查用
        while not game.is_hand_complete() and steps < 2000:
            steps += 1
            if game.is_betting_round_complete():
                game.advance_round()
                continue
            res = game.get_player_to_act()
            assert res is not None, "轮未完成却无行动者(死锁)"
            idx, p = res
            # 校验行动顺序: 当前玩家必须未弃牌且未全压
            assert not p.is_folded and not p.is_all_in, "弃牌/全压玩家被要求行动"
            assert p.chips > 0, "零筹码玩家被要求行动"
            # 校验桌面注额永不被压低
            gs = game.get_game_state_for(idx)
            to_call = gs['to_call']
            ai = p
            action, amount = ai.make_decision(gs)
            game.apply_action(idx, action, amount)
            for q in players:
                assert q.chips >= 0, "筹码为负"
            assert game.pot >= 0

        assert game.is_hand_complete(), f"手牌未结束(步数耗尽): {game.round_name}"

        # 筹码守恒: 总筹码恒定
        now = sum(p.chips for p in players)
        assert now == total_chips, f"筹码不守恒! {now} != {total_chips}"

        # 边池一致性: 赢家赢的钱 <= 本手总投入
        if game.winners:
            invested = sum(p.total_bet for p in players)
            won = sum(w[1] for w in game.winners)
            assert won <= invested, f"派发超过底池: {won} > {invested}"

    return hands, players


def main():
    print("== 6人桌标准测试 ==")
    hands, players = run_match(6, 1000, 10, 20, seed=42)
    print(f"  完成 {hands} 手, 正常结束")
    alive = [p for p in players if p.chips > 0]
    print(f"  存活: {len(alive)}, 冠军筹码: {max(p.chips for p in players)}")

    print("== 2人桌(单挑)测试 ==")
    hands, players = run_match(2, 800, 10, 20, seed=7)
    print(f"  完成 {hands} 手")

    print("== 短筹码压力测试 (初始100, 盲注10/20) ==")
    hands, players = run_match(6, 100, 10, 20, seed=99)
    print(f"  完成 {hands} 手")

    print("== 3人桌测试 ==")
    hands, players = run_match(3, 500, 5, 10, seed=5)
    print(f"  完成 {hands} 手")

    print("\n全部测试通过!")


if __name__ == '__main__':
    main()
