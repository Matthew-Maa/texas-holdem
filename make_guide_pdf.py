# -*- coding: utf-8 -*-
"""生成 玩家指南.pdf"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
FONT = 'STSong-Light'

BASE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(BASE, '玩家指南.pdf')

title_st = ParagraphStyle('title', fontName=FONT, fontSize=22, leading=30,
                          textColor=HexColor('#1a5c34'), alignment=1, spaceAfter=6)
h2 = ParagraphStyle('h2', fontName=FONT, fontSize=14, leading=20,
                    textColor=HexColor('#1a5c34'), spaceBefore=14, spaceAfter=6)
body = ParagraphStyle('body', fontName=FONT, fontSize=10.5, leading=17)
small = ParagraphStyle('small', fontName=FONT, fontSize=9, leading=14,
                       textColor=HexColor('#555555'))

doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=22*mm, rightMargin=22*mm,
                        topMargin=20*mm, bottomMargin=20*mm,
                        title='德州扑克 玩家指南', author='Kimi')

E = []
E.append(Paragraph('德州扑克 · 玩家指南', title_st))
E.append(Paragraph('Texas Hold\'em — AI 对战模拟器', ParagraphStyle('sub', fontName=FONT,
             fontSize=12, alignment=1, textColor=HexColor('#777777'))))
E.append(Spacer(1, 8))
E.append(HRFlowable(width='100%', color=HexColor('#1a5c34'), thickness=1.2))

E.append(Paragraph('一、游戏简介', h2))
E.append(Paragraph('本游戏是一个单机德州扑克模拟器：六种类型的 AI 玩家同场竞技，'
                   '你可以选择<b>观看 AI 对战</b>，或<b>亲自入座参与对战</b>。'
                   '游戏支持 2~6 人桌、可调初始资金与盲注级别，并内置背景音乐。', body))

E.append(Paragraph('二、主界面', h2))
E.append(Paragraph('启动游戏后进入主界面，包含以下入口：', body))
E.append(Paragraph(
    '• <b>观看 AI 对战</b>：全部座位由 AI 占据，自动连续进行牌局，直到只剩一名玩家。<br/>'
    '• <b>亲自参与对战</b>：你坐在正下方座位（0 号位），轮到你时屏幕下方会出现行动按钮。<br/>'
    '• <b>设置</b>：调整座位数、每个座位的 AI 类型、初始资金、盲注，以及音乐播放与音量。<br/>'
    '• <b>退出游戏</b>：画面缓慢变暗后退出。<br/>'
    '• <b>玩家指南</b>：主界面右下角按钮，点击后在浏览器中打开本 PDF。', body))

E.append(Paragraph('三、设置说明', h2))
E.append(Paragraph(
    '<b>座位数</b>：2~6 人桌。两人桌为单挑规则（庄家兼小盲）。<br/>'
    '<b>对手类型</b>：点击座位按钮可在六种 AI 之间切换（参与模式下 0 号位固定为你自己）。<br/>'
    '<b>初始资金</b>：每位玩家开局筹码，以大盲倍数步进调整。<br/>'
    '<b>盲注</b>：调整小盲，大盲自动为小盲的两倍。<br/>'
    '<b>音乐</b>：可开关、点击“下一首”切换曲目、拖动滑条调节音量。所有设置在退出后自动保存。', body))

E.append(Paragraph('四、对局操作', h2))
E.append(Paragraph('观看模式热键：', body))
E.append(Paragraph(
    '空格：暂停 / 继续　|　N：跳过等待立即开下一手　|　+ / -：调整 AI 行动速度　|　ESC：返回主菜单', body))
E.append(Paragraph('参与模式：轮到你行动时，屏幕下方会出现操作区：', body))
E.append(Paragraph(
    '• <b>弃牌</b>：放弃本手牌。<br/>'
    '• <b>过牌 / 跟注</b>：无需补注时为过牌，否则跟注到当前注额（筹码不足时自动为全压跟注）。<br/>'
    '• <b>加注到</b>：通过 − / + 调整目标注额（以一个大盲为步进），点击按钮执行加注。<br/>'
    '• <b>全压</b>：押上全部剩余筹码。', body))

E.append(Paragraph('五、AI 对手类型', h2))
data = [['类型', '风格特点'],
        ['岩石 Rock', '极紧极被动，只玩顶级牌，极少诈唬'],
        ['鲨鱼 Shark', '紧而激进，强牌加注、有选择地诈唬'],
        ['跟注站 Station', '松而被动，喜欢用中等牌跟到底'],
        ['疯子 Maniac', '松而激进，频繁加注和诈唬，波动极大'],
        ['均衡型 Balanced', '松紧适中，攻守平衡'],
        ['超紧 Nit', '比岩石更极端，几乎只玩超大对子']]
t = Table(data, colWidths=[30*mm, 120*mm])
t.setStyle(TableStyle([
    ('FONTNAME', (0, 0), (-1, -1), FONT),
    ('FONTSIZE', (0, 0), (-1, -1), 9.5),
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a5c34')),
    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
    ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#999999')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
]))
E.append(t)

E.append(Paragraph('六、规则速览', h2))
E.append(Paragraph(
    '每人发 2 张底牌，依次经历翻前、翻牌（3 张）、转牌、河牌共四轮下注，'
    '每轮可选择弃牌、过牌、跟注、下注、加注或全压。未弃牌玩家摊牌比大小，'
    '牌型从大到小为：皇家同花顺 ＞ 同花顺 ＞ 四条 ＞ 葫芦 ＞ 同花 ＞ 顺子 ＞ '
    '三条 ＞ 两对 ＞ 一对 ＞ 高牌（A-2-3-4-5 为最小顺子）。'
    '多人全压时按投入额度自动拆分主池与边池，分别结算。', body))

E.append(Spacer(1, 12))
E.append(HRFlowable(width='100%', color=HexColor('#cccccc'), thickness=0.6))
E.append(Paragraph('祝游戏愉快！设置与规则的任何调整都可在“设置”界面完成。', small))

doc.build(E)
print('已生成:', out)
