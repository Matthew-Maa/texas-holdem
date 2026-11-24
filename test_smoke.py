# -*- coding: utf-8 -*-
"""
整体冒烟测试 (SDL 无头模式):
1. 主菜单渲染
2. 设置界面: 改座位数/风格/筹码/盲注/音量/下一首
3. 观看模式: 连续运行 400 帧, 校验渲染与逻辑
4. 参与模式: 脚本化模拟人类点击按钮完成多个行动
5. 退出渐暗流程
"""

import os, sys
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
import main as M


def pump(app, n, scene=None):
    for _ in range(n):
        if scene and app.scene != scene:
            break
        for event in pygame.event.get():
            app.handle_event(event)
        app.update(1 / 30)
        app.render()


def main():
    app = M.App()
    print('场景:', app.scene)
    assert app.scene == 'menu'

    # --- 设置界面 ---
    app.show_settings()
    sc = app.settings_screen
    sc._on_control('seats_minus'); sc._on_control('seats_minus')  # 6 -> 4
    assert app.settings.num_seats == 4, app.settings.num_seats
    sc._on_control('style_1'); sc._on_control('chips_plus'); sc._on_control('sb_plus')
    sc._on_control('music_next')
    app.set_volume(0.7)
    sc.rebuild_rows()
    for _ in range(5):
        for event in pygame.event.get():
            app.handle_event(event)
        app.update(1/30); app.render()
    print('设置 OK: seats=%d chips=%d sb=%d vol=%.1f track=%s' % (
        app.settings.num_seats, app.settings.data['initial_chips'],
        app.settings.data['small_blind'], app.music.volume, app.music.current_name()))

    # --- 观看模式 ---
    app.settings.data['num_seats'] = 6
    app.settings.data['seat_styles'] = ['balanced', 'shark', 'station', 'maniac', 'rock', 'nit']
    app.settings.normalize()
    app.start_game('watch')
    pump(app, 1200, scene='game')
    g = app.game
    print('观看模式: hand=%d state=%s pot=%d' % (g.game.hand_num, g.state, g.game.pot))
    assert g.game.hand_num >= 2, "观看模式推进过慢"
    assert g.exit_to_menu is False

    # --- 参与模式 ---
    app.start_game('play')
    g = app.game
    assert isinstance(g.players[0], M.HumanPlayer)
    acted = 0
    for _ in range(30000):
        for event in pygame.event.get():
            app.handle_event(event)
        g.update(1/30)
        app.render()
        if g.awaiting_human:
            rects = g.human_button_rects()
            # 模拟点击: 循环使用不同动作, 覆盖所有按钮
            choice = acted % 6
            key = ['fold', 'check_call', 'raise', 'all_in', 'raise_minus', 'raise_plus'][choice]
            g.apply_human_action(key) if key in ('fold', 'check_call', 'raise', 'all_in') \
                else g.adjust_human_raise(1 if key == 'raise_plus' else -1)
            acted += 1
            if acted > 400:
                break
        if acted > 400:
            break
    print('参与模式: 人类行动 %d 次, hand=%d state=%s' % (acted, g.game.hand_num, g.state))
    assert acted >= 5, "人类行动未被触发"

    # ESC 返回菜单
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    app.handle_event(ev)
    assert app.scene == 'menu', app.scene

    # --- 退出渐暗 ---
    app.begin_quit()
    pump(app, 200)
    assert app.running is False
    print('退出渐暗 OK, fade=', app.fade_alpha)

    print('\n冒烟测试全部通过!')


if __name__ == '__main__':
    main()
