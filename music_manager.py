"""
德州扑克 - 背景音乐管理器
加载 music/ 目录下的曲目, 支持 播放/停止/下一首/音量调节。
"""

import os
import pygame


# 曲目顺序 (相对本文件的 music 目录)
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music')
# 把自己准备的 mp3 放进 music/ 目录，按下列文件名命名即可
# （本仓库不附带音频文件；缺文件时游戏正常运行，只是没有背景音乐）
TRACKS = [
    'bgm_1.mp3',
    'bgm_2.mp3',
    'bgm_3.mp3',
    'bgm_4.mp3',
]


class MusicManager:
    """简单的循环播放管理器"""

    def __init__(self, volume=0.5, enabled=True):
        self.track_idx = 0
        self.volume = max(0.0, min(1.0, volume))
        self.enabled = enabled
        self._started = False
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)  # 曲目自然结束事件
            self.available = True
        except pygame.error:
            self.available = False

    def _track_path(self, idx=None):
        if idx is None:
            idx = self.track_idx
        return os.path.join(MUSIC_DIR, TRACKS[idx % len(TRACKS)])

    def current_name(self):
        return TRACKS[self.track_idx % len(TRACKS)]

    def play(self):
        """从头播放当前曲目"""
        if not self.available or not self.enabled:
            return
        path = self._track_path()
        if not os.path.exists(path):
            # 音频文件不在（本仓库不附带音乐），静默跳过，不影响游戏
            self._started = False
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self._started = True
        except (pygame.error, OSError):
            self._started = False

    def next_track(self):
        """下一首并立即播放"""
        self.track_idx = (self.track_idx + 1) % len(TRACKS)
        was_playing = self._started
        if was_playing or self.enabled:
            self.play()

    def set_volume(self, volume):
        """设置音量 (0.0 - 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.available:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except (pygame.error, OSError):
                pass

    def toggle(self):
        """开/关音乐"""
        self.enabled = not self.enabled
        if not self.enabled and self.available:
            try:
                pygame.mixer.music.stop()
            except (pygame.error, OSError):
                pass
            self._started = False
        elif self.enabled:
            self.play()

    def handle_event(self, event):
        """处理曲目自然播完, 自动下一首"""
        if self.available and self.enabled and event.type == pygame.USEREVENT + 1:
            self.next_track()

    def shutdown(self):
        if self.available:
            pygame.mixer.music.stop()
