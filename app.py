"""猫溶溶：离线 Windows 毛绒果冻桌宠。"""
import json, math, os, random, sys, time
import numpy as np
from pathlib import Path
from audio_monitor import AudioMonitor
from companion_rules import CompanionRules
from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QSize, QUrl
from PySide6.QtGui import QMovie, QPainter, QColor, QFont, QFontDatabase, QAction, QIcon, QPixmap, QImage, QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QScrollArea, QFrame, QMenu, QSlider, QCheckBox, QSystemTrayIcon, QToolButton, QSpinBox, QTabWidget, QComboBox)

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = ROOT / 'assets'
APP_VERSION = '2026.10.23-r7'
ITEMS = json.loads((ASSETS / 'manifest.json').read_text(encoding='utf-8'))

def interpolate_frames(first,second,progress):
    """Interpolate premultiplied color AND alpha without additive coverage."""
    if second.isNull():return first
    if first is None or first.isNull():return second
    weight=max(0,min(256,round(progress*256)))
    if weight==256:return second
    first=first.scaled(second.size(),Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
    if weight==0:return first
    fmt=QImage.Format_RGBA8888_Premultiplied
    images=[p.toImage().convertToFormat(fmt) for p in (first,second)]
    arrays=[]
    for im in images:
        view=np.frombuffer(im.constBits(),dtype=np.uint8,count=im.height()*im.bytesPerLine())
        arrays.append(view.reshape(im.height(),im.bytesPerLine())[:,:im.width()*4].astype(np.uint16))
    pixels=((arrays[0]*(256-weight)+arrays[1]*weight+128)>>8).astype(np.uint8)
    result=QImage(pixels.data,second.width(),second.height(),pixels.strides[0],fmt).copy()
    return QPixmap.fromImage(result)

STYLE = '''
QWidget {background:#f8f5f1;color:#423d3c;font-family:"Microsoft YaHei UI";font-size:13px;}
QLabel#title {font-size:26px;font-weight:700;color:#453c40;}
QLabel#sub {color:#96868b;font-size:12px;}
QPushButton {background:#ece5df;border:0;border-radius:12px;padding:10px 16px;}
QPushButton:hover {background:#dfc9d0;}
QPushButton:pressed {background:#cfa9b6;}
QFrame#card {background:#fffdfb;border:1px solid #e9ded9;border-radius:18px;}
QScrollArea {border:0;background:transparent;}
QSlider::groove:horizontal {height:5px;background:#e8dcd9;border-radius:2px;}
QSlider::handle:horizontal {background:#b98c9d;width:15px;margin:-5px 0;border-radius:7px;}
QMenu {background:#fffaf7;border:1px solid #dfd1d1;padding:6px;}
QMenu::item {padding:8px 24px;}
QMenu::item:selected {background:#ead8df;}
'''

class Studio(QWidget):
    def __init__(self, pet):
        super().__init__()
        self.pet = pet
        self.setWindowTitle('猫溶溶小屋 · '+APP_VERSION)
        self.setWindowIcon(pet.windowIcon())
        self.resize(760, 720)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self); layout.setContentsMargins(26,24,26,20); layout.setSpacing(14)
        title = QLabel('猫溶溶小屋'); title.setObjectName('title'); layout.addWidget(title)
        sub = QLabel('Memento Mori~~'); sub.setObjectName('sub'); layout.addWidget(sub)
        self.status = QLabel(); layout.addWidget(self.status)
        self.tabs=QTabWidget();self.expressions=QWidget();self.setting_page=QWidget()
        self.expr_layout=QVBoxLayout(self.expressions);self.settings_layout=QVBoxLayout(self.setting_page)
        self.tabs.addTab(self.expressions,'互动与表情');self.tabs.addTab(self.setting_page,'设置')
        layout.addWidget(self.tabs,1)
        actions = QHBoxLayout()
        for text, fn in [('摸摸',pet.pat),('喂小鱼',pet.feed),('一起玩',pet.play),('睡 / 醒',pet.sleep_toggle),('情绪盒子',pet.emotion_box)]:
            b = QPushButton(text); b.clicked.connect(fn); actions.addWidget(b)
        self.expr_layout.addLayout(actions)
        settings = QHBoxLayout()
        settings.addWidget(QLabel('显示大小'))
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(120,600); self.slider.setValue(pet.pet_size)
        self.size_value=QSpinBox();self.size_value.setRange(120,600);self.size_value.setSuffix(' px');self.size_value.setValue(pet.pet_size)
        self.slider.valueChanged.connect(pet.set_size);self.size_value.valueChanged.connect(pet.set_size)
        settings.addWidget(self.slider);settings.addWidget(self.size_value)
        self.walk = QCheckBox('自由散步'); self.walk.setChecked(pet.roaming)
        self.walk.toggled.connect(pet.set_roaming); settings.addWidget(self.walk)
        top = QCheckBox('置顶'); top.setChecked(pet.on_top); top.toggled.connect(pet.set_top); settings.addWidget(top)
        self.settings_layout.addLayout(settings)
        row=QHBoxLayout()
        self.quiet=QCheckBox('闭嘴 · 封口并停止换表情和移动');self.quiet.setChecked(pet.quiet)
        self.quiet.toggled.connect(pet.set_quiet);row.addWidget(self.quiet)
        self.settings_layout.addLayout(row)
        self.setting_mascot=QLabel();self.setting_mascot.setFixedSize(360,270);self.setting_mascot.setAlignment(Qt.AlignCenter)
        self.settings_layout.addWidget(self.setting_mascot,0,Qt.AlignCenter)
        self.setting_movie=QMovie(str(ASSETS/'loops'/'13.webp'))
        self.setting_movie.setScaledSize(QSize(360,270));self.setting_movie.frameChanged.connect(lambda _:self.setting_mascot.setPixmap(self.setting_movie.currentPixmap()))
        self.settings_layout.addWidget(QLabel('滚轮也可以调整大小。闭嘴时不自动切换表情、不移动。'))
        audio=QCheckBox('跟随电脑音频 · 播放时常态变成哼歌');audio.setChecked(pet.audio_enabled)
        audio.toggled.connect(pet.set_audio_enabled);self.settings_layout.addWidget(audio)
        neutral_row=QHBoxLayout();neutral_row.addWidget(QLabel('常态预览 · 动作结束后随机选择'))
        self.idle_choice=QComboBox()
        for key,name in [('calm','平静'),('smile','微笑'),('rest','闭眼休息'),('curious','小惊讶')]:self.idle_choice.addItem(name,key)
        self.idle_choice.activated.connect(lambda index:pet.preview_idle(self.idle_choice.itemData(index)))
        neutral_row.addWidget(self.idle_choice);self.settings_layout.addLayout(neutral_row)
        self.settings_layout.addStretch()
        self.live=QLabel();self.live.setFixedSize(160,120);self.live.setAlignment(Qt.AlignCenter)
        self.expr_layout.addWidget(self.live,0,Qt.AlignCenter)
        self.expr_layout.addWidget(QLabel('表情收藏  /  26 个小心情 · 点击整张卡片即可互动'))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); grid = QGridLayout(content); grid.setSpacing(12)
        self.cards={}
        for i, item in enumerate(ITEMS):
            button = QToolButton();button.setCheckable(True)
            button.setStyleSheet('QToolButton{background:#fffdfb;border:1px solid #e9ded9;border-radius:16px;padding:8px;} QToolButton:hover{background:#f1e8e9;} QToolButton:checked{border:2px solid #b98c9d;background:#f1e8e9;}')
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIcon(QIcon(str(ASSETS/'hd'/f'{item["id"]:02}.png'))); button.setIconSize(QSize(125,96)); button.setMinimumHeight(158)
            button.clicked.connect(lambda checked=False,n=item['id']:pet.select_expression(n))
            tag={3:'60秒 · 双速散步',5:'30秒后进入酣睡2',7:'60秒 · 左键锁定',10:'5分钟后大哭',14:'1分钟后冒汗',16:'5分钟后害怕',20:'30秒 · 派对'}.get(item['id'],'短动作' if item.get('kind')=='action' else '持续状态')
            button.setText(f'{item["id"]:02} {item["name"]}\n{tag}');button.setMinimumWidth(150)
            self.cards[item['id']]=button;grid.addWidget(button,i//4,i%4)
        scroll.setWidget(content); self.expr_layout.addWidget(scroll,1)
        row = QHBoxLayout()
        idle=QPushButton('恢复常态');idle.clicked.connect(lambda:pet.select_expression(0));row.addWidget(idle)
        export = QPushButton('打开 GIF 文件夹'); export.clicked.connect(self.open_gifs); row.addWidget(export)
        hint = QLabel('拖动移动 · 单击互动 · 右键菜单'); hint.setObjectName('sub'); row.addWidget(hint)
        layout.addLayout(row)
        self.saved_setting_state=None;self.tabs.currentChanged.connect(self.tab_changed)
        self.update_status()
    def tab_changed(self,index):
        if index==1:self.setting_movie.start()
        else:self.setting_movie.stop()
        self.pet.settings_view(index==1)
    def closeEvent(self,event):
        if self.tabs.currentIndex()==1:self.tabs.setCurrentIndex(0)
        self.setting_movie.stop()
        super().closeEvent(event)
    def update_status(self):
        self.status.setText(f'亲密 {self.pet.affection}     饱腹 {self.pet.hunger}     精力 {self.pet.energy}   ·   {self.pet.current_name}')
        for n,card in self.cards.items():card.setChecked(n==self.pet.current_id)
        for control,value in [(self.quiet,self.pet.quiet),(self.slider,self.pet.pet_size),(self.size_value,self.pet.pet_size)]:
            control.blockSignals(True)
            control.setChecked(value) if isinstance(control,QCheckBox) else control.setValue(value)
            control.blockSignals(False)
    def open_gifs(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ASSETS/'gif')))

class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('Maorongrong','JellyCat')
        self.pet_size = int(self.settings.value('size',300))
        self.rules=CompanionRules(time.monotonic(),self.settings.value('affection',30),self.settings.value('hunger',75),self.settings.value('energy',80))
        self._rendered_revision=-1;self.settings_open=False;self.suppress_release_click=False
        self.roaming = self.settings.value('roaming','true') == 'true'
        self.on_top = self.settings.value('top','true') == 'true'
        self.idle_key=random.choice(['calm','smile','rest','curious'])
        self.next_blink=time.monotonic()+random.uniform(6,14);self.exiting=False
        self.audio_enabled=self.settings.value('audio','true')=='true';self.audio_active=False;self.audio_monitor=AudioMonitor()
        self.old_frame=None;self.fade_started=0
        self.pinned = False; self.current_name = '常态'; self.current_id = 0
        self.quiet=self.settings.value('quiet','false')=='true';self.transitioning=False
        self.next_expression=time.monotonic()+30
        self.velocity=(0,0);self.walk_position=None
        self.home_target=None;self.moving=False;self.move_angle=0
        self.clip_token=0;self.next_walk=time.monotonic()+random.uniform(35,75);self.walk_until=0;self.walk_fraction=0
        self.drag_start = None; self.dragged = False; self.last_action = time.monotonic(); self.until = 0
        self.movie = None; self.panel = None; self.bubble = ''; self.bubble_until = 0; self.direction = 1
        self.setWindowTitle('猫溶溶')
        self.setWindowIcon(QIcon(str(ASSETS/'hd'/'25.png')))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_flags(); self.set_size(self.pet_size)
        self.setCursor(Qt.OpenHandCursor)
        area = QApplication.primaryScreen().availableGeometry()
        self.move(int(self.settings.value('x',area.right()-self.width()-40)), int(self.settings.value('y',area.bottom()-self.height()-25)))
        self.clamp_position()
        self.rules.enter(1 if self.quiet else 0,time.monotonic());self._apply_rules(direct=True)
        self.tick_timer = QTimer(self); self.tick_timer.timeout.connect(self.tick); self.tick_timer.start(40)
        self.needs_timer = QTimer(self); self.needs_timer.timeout.connect(self.decay); self.needs_timer.start(60000)
        self.click_timer = QTimer(self); self.click_timer.setSingleShot(True); self.click_timer.timeout.connect(self.left_click)
        self.audio_timer=QTimer(self);self.audio_timer.timeout.connect(self.update_audio);self.audio_timer.start(200)
        self.tray = QSystemTrayIcon(self.windowIcon(),self)
        self.tray.setToolTip('猫溶溶 · 右键打开菜单')
        self.tray_menu=self.make_menu();self.tray.setContextMenu(self.tray_menu)
        self.tray_menu.aboutToShow.connect(self.sync_tray_menu)
        self.tray.activated.connect(lambda reason:self.open_panel() if reason==QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
    @property
    def affection(self):return self.rules.affection
    @affection.setter
    def affection(self,value):self.rules.affection=max(0,min(100,int(value)))
    @property
    def hunger(self):return self.rules.hunger
    @hunger.setter
    def hunger(self,value):self.rules.hunger=max(0,min(100,int(value)))
    @property
    def energy(self):return self.rules.energy
    @energy.setter
    def energy(self,value):self.rules.energy=max(0,min(100,int(value)))
    @property
    def quiet(self):return self.rules.quiet
    @quiet.setter
    def quiet(self,value):self.rules.quiet=bool(value)
    @property
    def sleeping(self):return self.rules.sleeping
    @property
    def sleep_started_at(self):return self.rules.sleep_started_at
    @sleep_started_at.setter
    def sleep_started_at(self,value):self.rules.sleep_started_at=value
    @property
    def next_expression(self):return self.rules.next_auto
    @next_expression.setter
    def next_expression(self,value):self.rules.next_auto=value

    def apply_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.on_top: flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
    def sync_tray_menu(self):
        values={'闭嘴':self.quiet,'自由散步':self.roaming,'保持当前表情':self.pinned}
        for action in self.tray_menu.actions():
            if action.text() in values:
                action.blockSignals(True);action.setChecked(values[action.text()]);action.blockSignals(False)
    def set_top(self,value):
        self.on_top=value; self.apply_flags(); self.show(); self.save()
    def set_roaming(self,value):
        self.roaming=value; self.save()
    def set_audio_enabled(self,value):
        self.audio_enabled=value;self.update_audio();self.save()
    def update_audio(self):
        if self.exiting:return
        active=self.audio_monitor.poll() if self.audio_enabled else False
        if active!=self.audio_active:
            self.audio_active=active
            if self.rules.state==0 and not self.quiet and not self.settings_open:self._show_expression(0,revision=self.rules.revision,keep_idle=True,direct=True)
    def set_size(self,value):
        self.pet_size=max(120,min(600,value));value=self.pet_size;self.resize(value,int(value*.75))
        if self.movie: self.movie.setScaledSize(QSize(value,int(value*.75)))
        self.clamp_position(); self.save()
        if self.panel:self.panel.update_status()
    def clamp_position(self):
        screen=QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        a=screen.availableGeometry()
        self.move(max(a.left(),min(self.x(),a.right()-self.width()+1)),max(a.top(),min(self.y(),a.bottom()-self.height()+1)))
    def save(self):
        for k,v in [('size',self.pet_size),('x',self.x()),('y',self.y()),('affection',self.affection),('hunger',self.hunger),('energy',self.energy),('roaming',str(self.roaming).lower()),('top',str(self.on_top).lower()),('quiet',str(self.quiet).lower()),('audio',str(self.audio_enabled).lower())]: self.settings.setValue(k,v)
    def play_clip(self,path,callback=None,bridge=True):
        self.old_frame=self.current_frame().copy() if bridge and self.movie else None
        self.fade_started=time.monotonic()
        self.clip_token+=1;token=self.clip_token
        if self.movie: self.movie.stop(); self.movie.deleteLater()
        webp=path.with_suffix('.webp')
        self.movie=QMovie(str(webp if webp.exists() else path))
        self.movie.setScaledSize(QSize(self.pet_size,int(self.pet_size*.75)))
        fired=False
        def frame_changed(frame):
            nonlocal fired
            if token!=self.clip_token:return
            self.update()
            if self.panel:self.panel.live.setPixmap(self.current_frame().scaled(128,96,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            if callback and not fired and frame==self.movie.frameCount()-1:
                fired=True
                # Transition files contain a loop flag for external viewing.
                # Stop the movie before its timer can wrap to frame zero;
                # the handoff timer then holds the final frame for its delay.
                delay=max(20,self.movie.nextFrameDelay())
                self.movie.setPaused(True)
                def done():
                    if token==self.clip_token:callback()
                QTimer.singleShot(delay,done)
        self.movie.frameChanged.connect(frame_changed); self.movie.start()
    def select_expression(self,n):
        if self.exiting:return
        if self.rules.select(n,time.monotonic()):
            self.pinned=False;self.walk_until=0;self.home_target=None;self.moving=False
            self._apply_rules(direct=True);self.save()
    def set_quiet(self,value):
        if self.exiting:return
        self.pinned=False;self.walk_until=0;self.home_target=None;self.moving=False
        self.rules.set_quiet(value,time.monotonic());self._apply_rules(direct=True);self.save()
    def preview_idle(self,key):
        if self.quiet or self.exiting or self.rules.left_locked(time.monotonic()):return
        self.idle_key=key;self.rules.select(0,time.monotonic());self._apply_rules(direct=True,keep_idle=True)
    def settings_view(self,opened):
        self.settings_open=opened
        self.rules.note_interaction(time.monotonic())
        if opened and not self.quiet:self._show_expression(13,revision=None,direct=True)
        else:self._rendered_revision=-1;self._apply_rules(direct=True)
    def express(self,n,seconds=None,keep_idle=False,direct=False,transition_clip=None):
        if self.exiting:return
        if self.rules.enter(n,time.monotonic()):
            self._apply_rules(direct=direct,keep_idle=keep_idle,transition_clip=transition_clip)
    def _apply_rules(self,direct=False,keep_idle=False,transition_clip=None):
        if self.exiting:return
        if self.settings_open and not self.quiet:
            self._rendered_revision=self.rules.revision
            self.rules.settled(self.rules.revision,self.rules.state,time.monotonic())
            if self.current_id!=13:self._show_expression(13,revision=None,direct=True)
            return
        if self._rendered_revision==self.rules.revision:return
        self._rendered_revision=self.rules.revision
        if self.rules.state!=0:self.home_target=None;self.moving=False;self.walk_until=0
        if self.rules.state in (1,7):self.drag_start=None;self.setCursor(Qt.OpenHandCursor)
        if self.rules.state==3:self.next_walk=time.monotonic()
        elif self.current_id==3:self.next_walk=time.monotonic()+random.uniform(45,100)
        if self.rules.transition_clip:transition_clip=ASSETS/'transitions'/(self.rules.transition_clip+'.gif')
        self._show_expression(self.rules.state,self.rules.revision,keep_idle,direct,transition_clip)
    def _show_expression(self,n,revision=None,keep_idle=False,direct=False,transition_clip=None):
        old=self.current_id
        if n==0 and not keep_idle:self.idle_key=random.choice(['calm','smile','rest','curious'])
        self.current_id=n;self.current_name=('常态 · '+{'calm':'平静','smile':'微笑','rest':'闭眼休息','curious':'小惊讶'}[self.idle_key]) if n==0 else ITEMS[n-1]['name']
        if n==0 and self.audio_active:self.current_name='常态 · 随音乐哼歌'
        self.next_blink=time.monotonic()+random.uniform(6,14)
        self.transitioning=True;self.until=float('inf');self.walk_until=0
        def loop():
            path=ASSETS/'loops'/f'{n:02}.gif' if n else ASSETS/'idles'/f'{self.idle_key}.gif'
            if n==0 and self.audio_active:path=ASSETS/'loops'/'17.gif'
            self.play_clip(path);self.transitioning=False
            if revision is not None:self.rules.settled(revision,n,time.monotonic())
            self.until=(self.rules.deadline or float('inf')) if n else 0
            if self.panel:self.panel.update_status()
        def enter():
            if n:self.play_clip(ASSETS/'transitions'/f'{n:02}_in.gif',loop)
            else:loop()
        if transition_clip is not None:self.play_clip(transition_clip,loop)
        elif old and old!=n and (not direct or n==0):self.play_clip(ASSETS/'transitions'/f'{old:02}_out.gif',enter)
        else:enter()
        self.last_action=time.monotonic()
        if self.panel:self.panel.update_status()
    def say(self,text):
        pass
    def left_click(self):
        if self.exiting:return
        if self.rules.left_click(time.monotonic()):self._apply_rules(direct=True);self.save()
    def _button(self,kind):
        if self.exiting:return
        if self.rules.button(kind,time.monotonic()):self._apply_rules(direct=True);self.save()
    def pat(self):self._button('pat')
    def feed(self):self._button('feed')
    def play(self):self._button('play')
    def sleep_toggle(self):self._button('sleep')
    def emotion_box(self):
        if self.exiting:return
        if self.rules.emotion_box(time.monotonic()):self._apply_rules(direct=True);self.save()
    def decay(self):
        self.save()
        if self.panel:self.panel.update_status()
    def tick(self):
        if self.exiting:return
        now=time.monotonic();before=(self.affection,self.hunger,self.energy)
        self.rules.tick(now,moving=self.moving,allow_auto=not self.settings_open and self.home_target is None and self.drag_start is None,busy=self.transitioning,pinned=self.pinned)
        self._apply_rules()
        if before!=(self.affection,self.hunger,self.energy):
            self.save()
            if self.panel:self.panel.update_status()
        was_moving=self.moving;self.moving=False
        if self.home_target is not None and not self.quiet and not self.rules.left_locked(now) and self.rules.state==0:
            dx,dy=self.home_target.x()-self.x(),self.home_target.y()-self.y();distance=math.hypot(dx,dy)
            if distance<=12:
                self.move(self.home_target);self.home_target=None;self.next_walk=now+random.uniform(45,100);self.express(0);self.save()
            else:
                self.move_angle=math.atan2(dy,dx);self.moving=True
                self.move(self.x()+round(dx/distance*12),self.y()+round(dy/distance*12))
            self.update();return
        flower=self.rules.flower
        if self.roaming and self.rules.state in (0,3) and not self.drag_start and not self.pinned and not self.quiet and not self.transitioning and not self.settings_open:
            if now>=self.next_walk:
                duration=random.uniform(3,6)
                self.walk_until=now+duration;self.next_walk=now+(duration if flower else random.uniform(45,100))
                angle=random.uniform(0,math.tau);speed=.8 if flower else .4
                self.velocity=(math.cos(angle)*speed,math.sin(angle)*speed)
                self.walk_position=[float(self.x()),float(self.y())]
            if now<self.walk_until:
                self.moving=True;self.move_angle=math.atan2(self.velocity[1],self.velocity[0])
                area=(QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()).availableGeometry()
                if self.walk_position is None:self.walk_position=[float(self.x()),float(self.y())]
                vx,vy=self.velocity;nx,ny=self.walk_position[0]+vx,self.walk_position[1]+vy
                if nx<area.left() or nx>area.right()-self.width()+1:vx=-vx
                if ny<area.top() or ny>area.bottom()-self.height()+1:vy=-vy
                self.velocity=(vx,vy);self.walk_position[0]+=vx;self.walk_position[1]+=vy
                self.move(round(self.walk_position[0]),round(self.walk_position[1]));self.clamp_position()
        if was_moving and not self.moving and self.rules.state==0 and not self.quiet and not self.settings_open:self._show_expression(0,self.rules.revision,direct=True)
        if self.rules.state==0 and not self.settings_open and not self.transitioning and not self.moving and not self.quiet and not self.audio_active and now>self.next_blink:
            self.next_blink=now+random.uniform(6,14)
            if self.idle_key in ('calm','curious'):
                key=self.idle_key
                self.play_clip(ASSETS/'idles'/f'{key}_blink.gif',lambda:self.play_clip(ASSETS/'idles'/f'{key}.gif',bridge=False),bridge=False)
        self.update()
    def current_frame(self):
        if not self.movie:return QPixmap()
        frame=self.movie.currentPixmap()
        progress=min(1,(time.monotonic()-self.fade_started)/.20)
        if self.old_frame is None or self.old_frame.isNull() or progress>=1:return frame
        return interpolate_frames(self.old_frame,frame,progress)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.moving:
            stretch=math.sin(time.monotonic()*9)*.035
            p.translate(self.width()/2,self.height()*.67);p.rotate(math.degrees(self.move_angle))
            p.scale(1+stretch,1-stretch*.7);p.rotate(-math.degrees(self.move_angle));p.translate(-self.width()/2,-self.height()*.67)
        if self.movie:p.drawPixmap(0,0,self.current_frame())
    def hit(self,pos):
        if not self.movie:return False
        im=self.movie.currentPixmap().toImage();x,y=int(pos.x()),int(pos.y())
        return 0<=x<im.width() and 0<=y<im.height() and im.pixelColor(x,y).alpha()>30
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton and self.hit(e.position()) and not self.quiet and not self.rules.left_locked(time.monotonic()):
            self.rules.note_interaction(time.monotonic())
            self.drag_start=e.globalPosition().toPoint();self.origin=self.pos();self.dragged=False;self.walk_until=0;self.setCursor(Qt.ClosedHandCursor)
    def mouseMoveEvent(self,e):
        if self.drag_start and not self.quiet and not self.rules.left_locked(time.monotonic()):
            delta=e.globalPosition().toPoint()-self.drag_start
            if delta.manhattanLength()>QApplication.startDragDistance():self.dragged=True
            if self.dragged:self.move(self.origin+delta)
    def mouseReleaseEvent(self,e):
        if self.suppress_release_click:
            self.suppress_release_click=False;self.drag_start=None;self.setCursor(Qt.OpenHandCursor);return
        if e.button()==Qt.LeftButton and self.drag_start:
            self.drag_start=None;self.setCursor(Qt.OpenHandCursor)
            if self.dragged:self.rules.note_interaction(time.monotonic());self.clamp_position();self.save()
            else:self.click_timer.start(QApplication.doubleClickInterval())
    def mouseDoubleClickEvent(self,e):
        if e.button()==Qt.LeftButton and self.hit(e.position()):
            self.click_timer.stop();self.suppress_release_click=True;self.drag_start=None;self.left_click()
    def wheelEvent(self,e):self.set_size(self.pet_size+(20 if e.angleDelta().y()>0 else -20))
    def contextMenuEvent(self,e):self.make_menu().exec(e.globalPos())
    def make_menu(self):
        menu=QMenu();menu.setStyleSheet(STYLE)
        for text,fn in [('猫溶溶小屋 · 全部表情',self.open_panel),('恢复常态',lambda:self.select_expression(0)),('摸摸',self.pat),('喂小鱼',self.feed),('一起玩',self.play),('睡觉 / 唤醒',self.sleep_toggle),('情绪盒子',self.emotion_box)]:menu.addAction(text,fn)
        menu.addSeparator()
        a=menu.addAction('闭嘴');a.setCheckable(True);a.setChecked(self.quiet);a.toggled.connect(self.set_quiet)
        size=menu.addMenu('显示大小')
        for px in (120,180,240,300,400,500,600):size.addAction(f'{px} px',lambda checked=False,value=px:self.set_size(value))
        a=menu.addAction('自由散步');a.setCheckable(True);a.setChecked(self.roaming);a.toggled.connect(self.set_roaming)
        a=menu.addAction('保持当前表情');a.setCheckable(True);a.setChecked(self.pinned);a.toggled.connect(self.pin)
        menu.addAction('回到屏幕右下角',self.home)
        menu.addSeparator();menu.addAction('退出猫溶溶',self.quit)
        return menu
    def pin(self,value):
        self.pinned=value;self.rules.note_interaction(time.monotonic())
        if value:self.walk_until=0;self.moving=False
    def home(self):
        if self.quiet or self.rules.left_locked(time.monotonic()):return
        self.show();a=QApplication.primaryScreen().availableGeometry()
        self.select_expression(0)
        if self.rules.state!=0:return
        self.home_target=QPoint(a.right()-self.width()-25,a.bottom()-self.height()-10)
        self.walk_until=0
    def open_panel(self):
        if not self.panel:self.panel=Studio(self)
        self.panel.update_status();self.panel.show();self.panel.raise_();self.panel.activateWindow()
    def quit(self):
        if self.exiting:return
        self.save();self.exiting=True;self.quiet=False;self.home_target=None;self.moving=False
        self.tick_timer.stop();self.click_timer.stop();self.needs_timer.stop();self.audio_timer.stop()
        if self.panel:self.panel.hide()
        self.tray.hide()
        self.play_clip(ASSETS/'transitions'/'26_in.gif',lambda:self.play_clip(ASSETS/'exits'/'melt.gif',QApplication.quit,bridge=False))
    def closeEvent(self,event):
        if self.exiting:event.accept()
        else:event.ignore();self.quit()

def main():
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    fontpath=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'msyh.ttc'
    if fontpath.exists():QFontDatabase.addApplicationFont(str(fontpath))
    app.setFont(QFont('Microsoft YaHei UI',9))
    # A second launch opens the existing companion's room.
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    socket=QLocalSocket();socket.connectToServer('maorongrong-desktop-pet-v1')
    if socket.waitForConnected(300):socket.write(b'open');socket.flush();socket.waitForBytesWritten(500);return 0
    QLocalServer.removeServer('maorongrong-desktop-pet-v1')
    server=QLocalServer();server.listen('maorongrong-desktop-pet-v1')
    pet=Pet();pet.show()
    def connection():
        s=server.nextPendingConnection()
        if s:s.disconnectFromServer();s.deleteLater()
        pet.open_panel()
    server.newConnection.connect(connection)
    if '--smoke-test' in sys.argv:
        pet.open_panel()
        def verify():
            try:
                assert pet.movie.isValid(),'Animation failed to load'
                for item in ITEMS:
                    m=QMovie(str(ASSETS/'loops'/f'{item["id"]:02}.webp'));assert m.isValid(),item
                meter=AudioMonitor();peak=meter.peak();assert meter.available,'Audio meter initialization failed'
                pet.panel.grab().save(str(ROOT/'preview.png'))
                pet.grab().save(str(ROOT/'pet-preview.png'))
                pet.panel.tabs.setCurrentIndex(1)
                pet.panel.grab().save(str(ROOT/'settings-preview.png'))
                (ROOT/'smoke-result.json').write_text(json.dumps({'animations':26,'audio_meter':meter.available,'peak':peak,'ok':True}),encoding='utf-8')
                print('SMOKE OK: 26 lossless animations, audio endpoint and UI')
                app.quit()
            except Exception:
                import traceback
                (ROOT/'smoke-error.txt').write_text(traceback.format_exc(),encoding='utf-8');app.exit(1)
        QTimer.singleShot(1500,verify)
    if '--exit-test' in sys.argv:QTimer.singleShot(400,pet.quit)
    return app.exec()

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        import traceback
        log=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Maorongrong'
        log.mkdir(exist_ok=True)
        (log/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
        raise
