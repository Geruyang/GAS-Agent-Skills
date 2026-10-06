"""Render bilingual GAS 2.0 diagrams from editable vector primitives.

Requires Pillow and a Chinese font; no runtime dependency of the skills.
Run from any directory: python docs/render_architecture.py
"""
from pathlib import Path
from html import escape
import argparse
import math
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/images/v2'
W, H, SCALE = 1800, 1380, 2
INK, MUTED, BLUE, TEAL, GOLD = '#17283F', '#50627A', '#285DAD', '#087D86', '#926017'
BG, LIGHT, BORDER = '#F5F7FB', '#EDF3FC', '#C7D5E7'


class Diagram:
    def __init__(self, lang, font, bold, title, desc):
        self.lang, self.font_path, self.bold_path = lang, font, bold
        self.im = Image.new('RGB', (W*SCALE, H*SCALE), BG)
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
                    f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>']
        self.rect(0, 0, W, H, BG, r=0)

    def tr(self, zh, en):
        return zh if self.lang == 'zh' else en

    def font(self, size, bold=False):
        return ImageFont.truetype(str(self.bold_path if bold else self.font_path), size*SCALE)

    def rect(self, x, y, w, h, fill='white', stroke=None, r=18):
        self.d.rounded_rectangle((x*SCALE, y*SCALE, (x+w)*SCALE, (y+h)*SCALE), radius=r*SCALE, fill=fill, outline=stroke, width=2*SCALE)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="2"/>')

    def text(self, x, y, s, size=25, color=INK, bold=False, center=False, maxw=None):
        font = self.font(size, bold)
        width = self.d.textlength(s, font=font)/SCALE
        assert maxw is None or width <= maxw, (s, width, maxw)
        left = x-width/2 if center else x
        assert left >= 0 and left+width <= W and y+size <= H, (s, left, y)
        self.d.text((left*SCALE, y*SCALE), s, font=font, fill=color, anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" dominant-baseline="text-before-edge" text-anchor="{"middle" if center else "start"}">{escape(s)}</text>')

    def paragraph(self, x, y, s, width, size=25, color=MUTED, leading=38):
        # Wrap English by word and Chinese by character; explicit newlines remain.
        for block in s.split('\n'):
            tokens = block.split(' ') if self.lang == 'en' else re.findall(r'[A-Za-z0-9_$][A-Za-z0-9_./+$…-]*|.',block)
            if self.lang == 'zh':
                joined=[]
                for token in tokens:
                    if token in '。，；：、）' and joined:
                        joined[-1]+=token
                    else:
                        joined.append(token)
                tokens=joined
            line = ''
            for token in tokens:
                candidate = (line+' '+token).strip() if self.lang == 'en' else line+token
                if self.d.textlength(candidate, font=self.font(size))/SCALE > width and line:
                    self.text(x, y, line, size, color, maxw=width)
                    y += leading
                    line = token
                else:
                    line = candidate
            if line:
                self.text(x, y, line, size, color, maxw=width)
                y += leading
        return y

    def line(self, points, color=BLUE, dashed=False, both=False):
        for (x1,y1),(x2,y2) in zip(points, points[1:]):
            length = math.hypot(x2-x1,y2-y1)
            if dashed:
                for start in range(0, int(length), 17):
                    end=min(start+10,length)
                    self.d.line(((x1+(x2-x1)*start/length)*SCALE,(y1+(y2-y1)*start/length)*SCALE,(x1+(x2-x1)*end/length)*SCALE,(y1+(y2-y1)*end/length)*SCALE),fill=color,width=3*SCALE)
            else:
                self.d.line((x1*SCALE,y1*SCALE,x2*SCALE,y2*SCALE),fill=color,width=3*SCALE)
        dash=' stroke-dasharray="10 7"' if dashed else ''
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="3"{dash}/>')
        for p,prev in [(points[-1],points[-2])] + ([(points[0],points[1])] if both else []):
            x,y=p; angle=math.atan2(y-prev[1],x-prev[0])
            pts=[p,(x-13*math.cos(angle)+6*math.sin(angle),y-13*math.sin(angle)-6*math.cos(angle)),(x-13*math.cos(angle)-6*math.sin(angle),y-13*math.sin(angle)+6*math.cos(angle))]
            self.d.polygon([(u*SCALE,v*SCALE) for u,v in pts],fill=color)
            self.svg.append(f'<polygon points="{" ".join(f"{u},{v}" for u,v in pts)}" fill="{color}"/>')

    def card(self, x, y, w, h, title, lines, accent=BLUE, size=29):
        self.rect(x,y,w,h,LIGHT,BORDER)
        self.rect(x+18,y+20,4,30,accent,r=2)
        self.text(x+w/2,y+22,title,size,INK,True,True,maxw=w-52)
        for i,txt in enumerate(lines):
            body_size=23
            while self.d.textlength(txt,font=self.font(body_size))/SCALE>w-28 and body_size>19:
                body_size-=1
            self.text(x+w/2,y+70+i*34,txt,body_size,MUTED,center=True,maxw=w-28)

    def save(self, name):
        OUT.mkdir(parents=True,exist_ok=True)
        self.im.save(OUT/(name+'.png'),optimize=True)
        (OUT/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>'])+'\n',encoding='utf-8',newline='\n')


def draw(mode, lang, font, bold):
    names = {'centralized':('集权开发模式','Centralized mode'), 'decentralized':('分权开发模式','Decentralized mode'), 'combined':('组合开发模式','Combined mode')}
    titles = names[mode]
    d = Diagram(lang,font,bold,titles[0 if lang=='zh' else 1], 'GAS 2.0: all governance roles are real subagents; the main session displays progress. N is configurable.')
    t=d.tr
    d.text(58,44,t(*titles),49,bold=True)
    subtitles={'centralized':('统一指挥 · 独立分析 · 并行开发','Unified direction · Independent analysis · Parallel work'), 'decentralized':('立规有界 · 执行自主 · 裁衡独立','Bounded rules · Autonomous execution · Independent judgment'), 'combined':('外层分权制衡 · 内层集中执行','Outer checks and balances · Inner centralized execution')}
    d.text(60,116,t(*subtitles[mode]),27,MUTED)
    d.rect(1520,54,220,50,LIGHT,r=25)
    d.text(1630,64,'GAS  /  2.0',25,BLUE,True,True)
    d.rect(40,185,1080,1120)
    d.rect(1144,185,616,1120)
    d.text(76,217,t('01  角色架构','01  Role architecture'),31,bold=True)
    d.text(1180,217,t('02  在 Codex 中使用','02  Use in Codex'),31,bold=True)
    human=t('人类用户／授权者','Human / authorizer')
    d.card(320,280,520,106,human,[t('目标 · 授权 · 预算 · 验收边界','Goals · Authorization · Budget · Acceptance')],size=30)
    if mode=='centralized':
        d.line([(580,386),(580,459)])
        d.text(608,408,t('授权与角色监督','Authorization / oversight'),22,BLUE)
        d.card(340,459,480,133,t('指挥者','Commander'),[t('拆分任务 · 主动并行 · 汇总裁决','Plan · Parallel dispatch · Decide'),t('集成 · 发布 · 回滚 · 回执','Integrate · Release · Roll back')],size=32)
        for x in (232,580,928):
            d.line([(580,592),(580,620),(x,620),(x,675)])
        d.rect(477,628,206,32)
        d.text(580,631,t('派工与协调','Assign / coordinate'),22,BLUE,center=True)
        roles(d,675)
        evidence(d,860)
        d.rect(76,965,1008,154,'#F2F6FC',r=14)
        d.text(100,985,t('所有下属向指挥者汇报','All subordinate roles report to the commander'),27,bold=True)
        d.paragraph(100,1032,t('执行成果与验证证据／审查问题分析／监督与安全告警。\n监督者核对执行与审查是否符合指挥者意图。','Implementation and verification evidence; review findings; monitoring and safety alerts. Supervision checks execution and review against commander intent.'),955,24,leading=35)
    elif mode=='decentralized':
        d.line([(450,386),(450,423),(268,423),(268,493)])
        d.line([(710,386),(710,423),(892,423),(892,493)])
        d.text(580,449,t('三类职责平级 · 不兼权','Three peer functions · Separate powers'),24,TEAL,True,True)
        d.card(88,493,360,177,t('立规者','Rulemaker'),[t('制定规则与验收标准','Define rules and acceptance'),t('受理复议 · 修订规则','Consider appeals · Revise rules')],TEAL)
        d.card(712,493,360,177,t('裁衡者','Arbiter'),[t('审查规则与人类意图','Review rules against intent'),t('分析成果与监控证据','Analyze results and evidence'),t('不编写测试／验证代码','No test / verification coding')],TEAL)
        d.line([(460,564),(700,564)],TEAL,both=True)
        d.text(580,526,t('规则送审','Submit rules'),22,TEAL,center=True)
        d.text(580,587,t('意图审查／异议','Intent review / objections'),20,TEAL,center=True)
        d.line([(268,670),(268,727),(444,727),(444,812)],both=True)
        d.line([(892,670),(892,727),(716,727),(716,812)],TEAL,both=True)
        d.text(270,753,t('规则／复议','Rules / appeals'),23,BLUE,center=True)
        d.text(895,753,t('成果／裁衡','Evidence / judgment'),23,TEAL,center=True)
        d.card(340,812,480,170,t('执行者 1…N','Executors 1…N'),[t('独立分工 · 并行实施','Independent tasks · Parallel work'),t('各自编写测试代码并完成验证','Each owns test code and verification'),t('共享运行事实与异常证据','Share runtime facts and anomalies')])
        d.line([(580,982),(580,1022)])
        d.rect(88,1022,984,99,'#F2F6FC',r=14)
        d.text(580,1040,t('有效规则 + 独立裁衡 + 适用授权','Effective rules + Independent judgment + Authorization'),26,bold=True,center=True)
        d.text(580,1083,t('获准交付 → 阶段复盘 → 改规建议','Authorized delivery → Retrospective → Rule proposals'),23,MUTED,center=True)
    else:
        d.line([(580,386),(580,456)])
        d.rect(72,415,1016,264,'#F1FAFB','#ABD7DB',r=15)
        d.text(96,434,t('外层：三席平级制衡','Outer layer: three peer seats'),25,TEAL,True)
        d.card(92,488,304,156,t('立规者','Rulemaker'),[t('制定规则与验收','Define rules / acceptance'),t('受理规则复议','Consider rule appeals')],TEAL,28)
        d.card(428,488,304,156,t('外层执行者','Outer executor'),[t('= 内层指挥者','= Inner commander'),t('同一身份 · 同一任期','One identity · One term')],TEAL,28)
        d.card(764,488,304,156,t('裁衡者','Arbiter'),[t('审查意图与成果','Review intent / results'),t('分析证据 · 不写测试','Analyze evidence; no tests')],TEAL,28)
        d.line([(399,563),(425,563)],TEAL,both=True)
        d.line([(735,563),(761,563)],TEAL,both=True)
        d.rect(72,716,1016,314,'#F7FAFF',BORDER,r=15)
        d.text(96,733,t('内层：统一指挥，主动并行','Inner layer: coordinated parallel work'),25,BLUE,True)
        for x in (232,580,928):
            d.line([(580,644),(580,776),(x,776),(x,806)])
        roles(d,806,compact=True)
        d.rect(92,986,976,31,'#EAF1FB',r=6)
        d.text(580,989,t('执行与监控输出 → 审查分析 → 指挥者汇总','Execution + monitoring → Review analysis → Commander'),22,BLUE,center=True)
        gates=[t('内层接受','Inner acceptance'),t('集成与重验','Integrate / recheck'),t('外层裁衡','Outer judgment'),t('获准交付','Authorized delivery')]
        for i,label in enumerate(gates):
            x=80+i*255
            d.rect(x,1070,233,53,'#FFF8E9','#E6D4AE',r=10)
            d.text(x+116.5,1085,label,20 if lang=='en' else 22,GOLD,True,True,maxw=218)
            if i<3:d.line([(x+234,1096),(x+253,1096)],GOLD)
    d.rect(76,1163,1008,99,'#F0F3F7',r=14)
    d.text(100,1181,t('主会话：进展展示与人类交互','Main session: progress display and human interaction'),26,bold=True)
    d.text(100,1225,t('所有治理角色均由真实子 agent 承担，主会话不占角色席位。','All governance roles are real subagents; the main session holds no role.'),23,MUTED,maxw=960)
    guide(d,mode)
    d.text(60,1330,t('实线：授权／派工／规则关系    青色：证据与分析    N：用户指定的执行者人数，默认 1','Solid lines: authority / assignments / rules    Teal: evidence / analysis    N: user-selected executor count; default 1'),23,MUTED,maxw=1680)
    prefix={'centralized':'01','decentralized':'02','combined':'03'}[mode]
    d.save(prefix+'-'+mode+('-en' if lang=='en' else ''))


def roles(d,y,compact=False):
    t=d.tr
    w=312; h=168 if compact else 185
    data=[(t('执行者 1…N','Executors 1…N'),[t('独立任务开发','Own independent tasks'),t('编写测试／验证代码','Write tests / verification'),t('完成验证并提交证据','Run checks; submit evidence')]),
          (t('审查者','Reviewer'),[t('接收执行与监督输出','Read work / monitor output'),t('分析问题与证据缺口','Analyze issues / evidence gaps'),t('不编写测试／验证代码','No test / verification coding')]),
          (t('监督者','Supervisor'),[t('核对指挥意图与行为','Check intent and behavior'),t('监控软硬件与工作状态','Monitor systems / agent status'),t('异常与安全告警上报','Report anomalies / safety')])]
    for x,(title,lines) in zip((76,424,772),data):
        d.card(x,y,w,h,title,lines,size=28)


def evidence(d,y):
    for x in (232,928):
        d.line([(x,y),(x,y+48),(580,y+48),(580,y)],TEAL)
    d.text(580,y+66,d.tr('开发与验证输出 + 监控与异常输出 → 审查分析','Implementation / verification + Monitoring / anomalies → Review'),23,TEAL,center=True)


def guide(d,mode):
    t=d.tr
    count={'centralized':('N+3','4'),'decentralized':('N+2','3'),'combined':('N+5','6')}[mode]
    def step(n,y,title,body):
        d.rect(1180,y,40,40,LIGHT,r=10)
        d.text(1200,y+5,str(n),25,BLUE,True,True)
        d.text(1238,y+3,title,27,bold=True,maxw=480)
        return d.paragraph(1238,y+56,body,468,24,leading=36)
    step(1,281,t('读取技能与协议','Read the Skill and protocol'),t('在实际项目中读取完整 SKILL.md\n及关联协议。组合模式需将三个\n技能目录保持同级。','In the target project, read SKILL.md and its protocol. Combined mode requires all three sibling skill folders.'))
    d.rect(1180,471,548,84,'#F2F6FC',r=12)
    d.text(1202,486,t('安装并识别后，可按名称调用：','After installation and discovery:'),22,MUTED)
    d.text(1202,524,'$gas-'+mode+'-development',22,BLUE,maxw=508)
    step(2,595,t('确认职责与团队','Confirm roles and the team'),t(f'执行者人数 N 可由用户指定。\n治理团队：{count[0]} 个真实子 agent。\n另加 1 个主会话。\n默认 N=1：{count[1]} 个治理子 agent。',f'Choose N executors: {count[0]} real subagents plus one main session. With N=1, use {count[1]} subagents.'))
    d.paragraph(1238,807,t('确认模型、推理强度及职责；\n全员就绪后开始。','Confirm models, reasoning effort and roles. Wait for the whole team.'),468,23,leading=34)
    if mode=='decentralized':
        step(3,902,t('独立执行与裁衡','Execute and judge independently'),t('执行者在有效契约内并行开发和验证。裁衡者分析成果及监控证据；补充测试交具名执行者。','Executors implement and verify in parallel under the effective contract. The arbiter analyzes outputs; named executors add any missing tests.'))
        note=t('三类职责保持平级；\n不增加指挥者或监督者。','Three functions remain peers.\nNo commander or supervisor is added.')
    else:
        step(3,902,t('并行开发、审查与监控','Run ready work in parallel'),t('指挥者主动安排独立任务。执行、已有输出审查及监控可并行；真实依赖和共享设备按需串行。','The commander dispatches ready independent tasks. Implementation, review of ready outputs and monitoring overlap; dependencies and shared devices constrain concurrency.'))
        note=t('监督重点：电压／电流、运行与 agent 状态、软硬件异常。缺测或过期读数不能认定安全。','Monitor voltage/current, runtime, agents and system faults. Missing or stale readings never establish safety.')
    d.rect(1180,1163,548,99,'#FFF8E9',r=14)
    end=d.paragraph(1200,1178,note,506,21,GOLD,leading=29)
    assert end-29+21<=1257, end


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/msyh.ttc'))
    parser.add_argument('--bold-font',type=Path,default=Path('C:/Windows/Fonts/msyhbd.ttc'))
    args=parser.parse_args()
    for language in ('zh','en'):
        for mode in ('centralized','decentralized','combined'):
            draw(mode,language,args.font,args.bold_font)
    print('Rendered 3 architectures in Chinese and English as PNG and SVG:',OUT)
