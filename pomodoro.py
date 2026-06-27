"""
Focus — 学习专注计时器
运行: python pomodoro.py
依赖: 纯 Python 3.x
"""

import tkinter as tk
from tkinter import messagebox
import winsound
import json
import os
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(HERE, "focus_history.json")
SETTINGS_FILE = os.path.join(HERE, "focus_settings.json")

def _load_categories():
    """从设置文件加载自定义科目，失败则返回默认"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return ["数学", "英语", "编程", "阅读", "写作", "物理", "化学", "其他"]

# ═══════════════════════════════════════
#  Token: "冷墨" Cool Ink — 浅色主题
# ═══════════════════════════════════════
T = {
    "bg":       "#f5f4f0",   # 冷调纸白
    "surface":  "#ecebe6",   # 卡片面
    "accent":   "#3a6b8c",   # 墨蓝 — 唯一强调
    "accent_d": "#2d5a78",   # 墨蓝深（按钮 hover）
    "sage":     "#5d9b82",   # 鼠尾草 — 完成态
    "text":     "#1f1e1c",   # 墨黑
    "dim":      "#91908b",   # 铅灰
    "ring_bg":  "#e2e0da",   # 环底
    "danger":   "#b85c5c",   # 暖红
    "danger_d": "#a04a4a",   # 暖红深（按钮 hover）
    "hover":    "#dddbd4",   # chip hover
    "white":    "#ffffff",
}

F = {
    "display":  ("Microsoft YaHei", 20, "bold"),
    "title":    ("Microsoft YaHei", 15, "bold"),
    "body":     ("Microsoft YaHei", 11),
    "timer":    ("Cascadia Code", 36, "bold"),
    "caption":  ("Microsoft YaHei", 10),
    "small":    ("Microsoft YaHei", 9),
    "wheel":    ("Cascadia Code", 14, "bold"),
    "chip":     ("Microsoft YaHei", 10),
    "number":   ("Cascadia Code", 12, "bold"),
}

DONUT_COLORS = ["#3a6b8c", "#5d9b82", "#c4874a", "#b85c5c",
                "#7e8cc4", "#8ea87e", "#c49a6e", "#a07ea8"]


class FocusApp:
    """Focus — 可缩放三页式学习计时器"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("专注")
        self.window.geometry("420x600")
        self.window.minsize(400, 580)
        self.window.resizable(True, True)
        self.window.configure(bg=T["bg"])

        self.remaining = 25 * 60
        self.total_seconds = 25 * 60
        self.is_running = False
        self.is_paused = False
        self.current_category = ""
        self.after_id = None
        self.history = self._load_history()
        self.categories = _load_categories()

        # ── 三页 ──
        self.pages = {}
        for name in ["setup", "timer", "history"]:
            f = tk.Frame(self.window, bg=T["bg"])
            f.place(x=0, y=0, relwidth=1, relheight=1)
            self.pages[name] = f

        self._build_setup()
        self._build_timer()
        self._build_history()
        self._show("setup")

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════════════════════════════
    #  页面切换
    # ═══════════════════════════════════════

    def _show(self, name):
        self.pages[name].tkraise()
        if name == "setup":
            self._refresh_setup_chips()
        elif name == "history":
            self._render_history()

    # ═══════════════════════════════════════
    #  第 1 页 · 设定
    # ═══════════════════════════════════════

    def _build_setup(self):
        p = self.pages["setup"]

        # ── 底部栏（固定高度，永不缩小） ──
        bottom_bar = tk.Frame(p, bg=T["bg"], height=40)
        bottom_bar.pack(side="bottom", fill="x")
        bottom_bar.pack_propagate(False)

        hist = tk.Label(bottom_bar, text="查看记录  →", font=F["caption"],
                        fg=T["dim"], bg=T["bg"], cursor="hand2")
        hist.place(relx=0.5, rely=0.5, anchor="center")
        hist.bind("<Button-1>", lambda e: self._show("history"))
        for ev in ["<Enter>", "<Leave>"]:
            hist.bind(ev, lambda e, l=hist, on=ev == "<Enter>":
                      l.config(fg=T["accent"] if on else T["dim"]))

        # ── 按钮区（固定高度，贴底部栏上方，不会被遮挡） ──
        btn_bar = tk.Frame(p, bg=T["bg"], height=64)
        btn_bar.pack(side="bottom", fill="x")
        btn_bar.pack_propagate(False)

        self._rounded_btn(btn_bar, "开始专注", T["accent"], T["white"],
                          self._begin_session, 170, 44).place(relx=0.5, rely=0.5, anchor="center")

        # ── 内容区（填满剩余空间） ──
        content = tk.Frame(p, bg=T["bg"])
        content.pack(fill="both", expand=True)

        tk.Label(content, text="新建专注", font=F["display"],
                 fg=T["text"], bg=T["bg"]).pack(pady=(44, 2))
        tk.Label(content, text="设定时长，选择科目",
                 font=F["caption"], fg=T["dim"], bg=T["bg"]).pack()

        # 滚轮
        wheel_wrapper = tk.Frame(content, bg=T["bg"])
        wheel_wrapper.pack(pady=(32, 12))

        self._build_wheel(wheel_wrapper, "hour", 25, 0, "时")
        tk.Label(wheel_wrapper, text=":", font=("Cascadia Code", 24, "bold"),
                 fg=T["dim"], bg=T["bg"]).pack(side="left", padx=6)
        self._build_wheel(wheel_wrapper, "minute", 60, 25, "分")

        # 科目
        tk.Label(content, text="你要学什么？", font=F["caption"],
                 fg=T["dim"], bg=T["bg"]).pack(pady=(28, 8))

        self.cat_var = tk.StringVar(value="")
        self.cat_entry = tk.Entry(
            content, textvariable=self.cat_var,
            font=F["body"], bg=T["surface"], fg=T["text"],
            insertbackground=T["text"], relief="flat",
            width=22, justify="center", bd=0,
        )
        self.cat_entry.pack(ipady=6)

        # chip 行 + 齿轮
        chip_row = tk.Frame(content, bg=T["bg"])
        chip_row.pack(pady=(10, 0))
        for cat in self.categories[:6]:
            self._chip(chip_row, cat)

        # 齿轮放在 chip 行末尾
        gear = tk.Label(chip_row, text=" ⚙", font=("Microsoft YaHei", 11),
                        fg=T["dim"], bg=T["bg"], cursor="hand2")
        gear.pack(side="left", padx=2)
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>", lambda e: gear.config(fg=T["accent"]))
        gear.bind("<Leave>", lambda e: gear.config(fg=T["dim"]))

    def _build_wheel(self, parent, tag, count, default_idx, suffix):
        """滚轮选择器 — 单步滚动 + 选中居中 + 上下限"""
        frame = tk.Frame(parent, bg=T["bg"])
        frame.pack(side="left", padx=10)

        tk.Label(frame, text=suffix, font=F["caption"],
                 fg=T["dim"], bg=T["bg"]).pack()

        wheel_h = 160
        wheel_w = 56
        VISIBLE = 5

        container = tk.Frame(frame, bg=T["surface"],
                             width=wheel_w, height=wheel_h)
        container.pack(pady=(4, 0))
        container.pack_propagate(False)

        lb = tk.Listbox(
            container,
            height=VISIBLE, width=3, font=F["wheel"],
            bg=T["surface"], fg=T["dim"],
            selectbackground=T["surface"], selectforeground=T["accent"],
            relief="flat", highlightthickness=0,
            exportselection=False, activestyle="none",
        )
        for i in range(count):
            lb.insert("end", f"{i:02d}")
        lb.place(x=0, y=0, relwidth=1, relheight=1)

        # 初始选中 — 居中
        lb.selection_clear(0, "end")
        lb.selection_set(default_idx)
        lb.itemconfig(default_idx, fg=T["accent"])
        self._center_wheel_item(lb, default_idx, count, VISIBLE)

        var = tk.StringVar(value=f"{default_idx:02d}")
        setattr(self, f"_{tag}_var", var)

        def reset_all_items():
            for i in range(count):
                lb.itemconfig(i, fg=T["dim"])

        def on_select(e, lst=lb, v=var):
            sel = lst.curselection()
            if sel:
                idx = sel[0]
                v.set(f"{idx:02d}")
                reset_all_items()
                lst.itemconfig(idx, fg=T["accent"])

        lb.bind("<<ListboxSelect>>", on_select)

        def on_mousewheel(e, lst=lb, cnt=count, vis=VISIBLE):
            """滚轮仅滚动视图，不改变选中；用户点击才选中"""
            delta = -1 if e.delta > 0 else 1
            denom = cnt - vis
            if denom <= 0:
                return "break"
            # 精确追踪顶部项，每次只滚 1 行
            top_frac = lst.yview()[0]
            current_top = int(top_frac * denom + 0.5)
            new_top = max(0, min(denom, current_top + delta))
            lst.yview_moveto(new_top / denom)
            return "break"

        # 滚轮绑定到 listbox、容器（任何位置都能滚）
        for w in [lb, container, frame]:
            w.bind("<MouseWheel>", on_mousewheel)

        setattr(self, f"_{tag}_list", lb)

    def _chip(self, parent, text):
        c = tk.Label(parent, text=text, font=F["chip"],
                     fg=T["dim"], bg=T["surface"],
                     padx=12, pady=5, cursor="hand2")
        c.pack(side="left", padx=3)
        c.bind("<Button-1>", lambda e, t=text: self.cat_var.set(t))
        c.bind("<Enter>", lambda e, w=c: w.config(fg=T["accent"], bg=T["hover"]))
        c.bind("<Leave>", lambda e, w=c: w.config(fg=T["dim"], bg=T["surface"]))

    def _begin_session(self):
        h = int(self._hour_var.get() or "0")
        m = int(self._minute_var.get() or "25")
        total = h * 3600 + m * 60
        if total == 0:
            messagebox.showwarning("无法计时", "时长不能为 00:00，请重新选择。")
            return
        total = max(1, min(total, 24 * 3600))

        self.total_seconds = total
        self.remaining = total
        self.current_category = self.cat_var.get().strip() or "学习"
        self.is_running = False
        self.is_paused = False

        self._sync_timer_page()
        self._set_btn_state("ready")
        self._show("timer")

    # ═══════════════════════════════════════
    #  第 2 页 · 计时（新按钮流 + hh:mm:ss）
    # ═══════════════════════════════════════

    def _build_timer(self):
        p = self.pages["timer"]

        # ── 顶栏（仅显示科目，无 Stop） ──
        bar = tk.Frame(p, bg=T["bg"], height=36)
        bar.pack(fill="x", padx=24, pady=(28, 0))
        bar.pack_propagate(False)

        self._timer_cat = tk.Label(bar, text="", font=F["title"],
                                   fg=T["accent"], bg=T["bg"])
        self._timer_cat.pack(side="left")

        # ── 环形进度（Canvas 居中） ──
        self._timer_canvas = tk.Canvas(p, bg=T["bg"], highlightthickness=0, highlightbackground=T["bg"])
        self._timer_canvas.pack(expand=True, fill="both", padx=20, pady=(10, 0))

        # 在首次绘制和 resize 时重绘环
        self._timer_canvas.bind("<Configure>", self._on_canvas_resize)
        self._ring_drawn = False

        # 状态文字
        self._timer_status = tk.Label(
            p, text="准备就绪", font=F["caption"],
            fg=T["dim"], bg=T["bg"],
        )
        self._timer_status.pack(pady=(0, 10))

        # ── 按钮区（可动态切换 1 或 2 按钮） ──
        self._btn_shelf = tk.Frame(p, bg=T["bg"])
        self._btn_shelf.pack(pady=(0, 14))

        # 预建两个按钮 Label
        self._btn_a = tk.Label(
            self._btn_shelf, text="", font=F["body"],
            padx=32, pady=10, cursor="hand2",
        )
        self._btn_b = tk.Label(
            self._btn_shelf, text="", font=F["body"],
            padx=32, pady=10, cursor="hand2",
        )

        # 底部提示
        self._timer_hint = tk.Label(
            p, text="", font=F["small"],
            fg=T["dim"], bg=T["bg"],
        )
        self._timer_hint.pack()

    def _on_canvas_resize(self, event):
        """窗口缩放时重绘环形进度（防抖：停止缩放 150ms 后才重绘）"""
        if event.width < 50 or event.height < 50:
            return
        # 取消之前的 pending 重绘
        if hasattr(self, "_resize_after_id") and self._resize_after_id:
            self.window.after_cancel(self._resize_after_id)
        self._resize_after_id = self.window.after(
            150, lambda: self._draw_ring(event.width, event.height)
        )

    def _draw_ring(self, cw, ch):
        can = self._timer_canvas
        can.delete("all")

        cx, cy = cw // 2, ch // 2
        ring_r = min(cx, cy) - 12
        ring_w = max(8, ring_r // 11)
        ring_r -= ring_w // 2

        self._ring_cx = cx
        self._ring_cy = cy
        self._ring_r = ring_r
        self._ring_w = ring_w

        # 背景环
        can.create_oval(
            cx - ring_r, cy - ring_r,
            cx + ring_r, cy + ring_r,
            outline=T["ring_bg"], width=ring_w, fill="",
        )

        # 前景弧
        pct = 0.0
        if self.total_seconds > 0:
            pct = (self.total_seconds - self.remaining) / self.total_seconds
        extent = -359 * pct
        color = T["sage"] if self.remaining == 0 else T["accent"]

        self._ring_arc = can.create_arc(
            cx - ring_r, cy - ring_r,
            cx + ring_r, cy + ring_r,
            outline=color, width=ring_w,
            style="arc", start=90, extent=extent,
        )
        self._ring_canvas_ref = can

        # 中心计时文字
        font_size = max(20, ring_r // 4)
        timer_font = ("Cascadia Code", font_size, "bold")
        self._timer_label = can.create_text(
            cx, cy, text=self._fmt(self.remaining),
            font=timer_font, fill=T["text"],
        )

        self._ring_drawn = True

    def _sync_timer_page(self):
        self._timer_cat.config(text=self.current_category)
        self._timer_status.config(text="准备就绪", fg=T["dim"])
        self._timer_hint.config(text="")
        self._ring_drawn = False  # 触发重绘
        # 立刻触发一次绘制
        cw = self._timer_canvas.winfo_width()
        ch = self._timer_canvas.winfo_height()
        if cw > 50 and ch > 50:
            self._draw_ring(cw, ch)

    def _set_btn_state(self, state):
        """ready | running | paused"""
        # 清除按钮区
        self._btn_a.pack_forget()
        self._btn_b.pack_forget()

        def make(lbl, text, bg, fg, hover_bg, cmd):
            lbl.config(text=text, bg=bg, fg=fg,
                       relief="flat", cursor="hand2")
            lbl.unbind("<Button-1>")
            lbl.bind("<Button-1>", lambda e: cmd())
            # hover 效果
            lbl.unbind("<Enter>")
            lbl.unbind("<Leave>")
            lbl.bind("<Enter>", lambda e, b=bg, h=hover_bg, l=lbl:
                     l.config(bg=h))
            lbl.bind("<Leave>", lambda e, b=bg, l=lbl:
                     l.config(bg=b))

        if state == "ready":
            # 仅一个按钮：开始
            make(self._btn_a, "▶  开始", T["accent"], T["white"],
                 T["accent_d"], self._start)
            self._btn_a.pack()

        elif state == "running":
            # 仅一个按钮：暂停
            make(self._btn_a, "⏸  暂停", T["accent"], T["white"],
                 T["accent_d"], self._pause)
            self._btn_a.pack()

        elif state == "paused":
            # 两个按钮：继续 + 结束
            make(self._btn_a, "▶  继续", T["accent"], T["white"],
                 T["accent_d"], self._start)
            make(self._btn_b, "结束", T["danger"], T["white"],
                 T["danger_d"], self._end)
            self._btn_a.pack(side="left", padx=8)
            self._btn_b.pack(side="left", padx=8)

    # ── 计时操作 ──

    def _start(self):
        self.is_running = True
        self.is_paused = False
        self._set_btn_state("running")
        self._timer_status.config(text="专注中...", fg=T["accent"])
        self._timer_hint.config(text="")
        self._tick()

    def _pause(self):
        self.is_running = False
        self.is_paused = True
        self._set_btn_state("paused")
        self._timer_status.config(text="已暂停", fg=T["dim"])
        self._timer_hint.config(text="")
        if self.after_id:
            self.window.after_cancel(self.after_id)
            self.after_id = None

    def _end(self):
        elapsed = self.total_seconds - self.remaining
        if elapsed > 0:
            self._save(self.current_category, elapsed)
        self._show("setup")

    def _tick(self):
        if not self.is_running:
            return
        if self.remaining > 0:
            self.remaining -= 1
            self._update_display()
            self.after_id = self.window.after(1000, self._tick)
        else:
            self._done()

    def _done(self):
        self.is_running = False
        self._play_beep()
        self._save(self.current_category, self.total_seconds)
        self._update_display()
        self._timer_status.config(text="完成！", fg=T["sage"])
        self._set_btn_state("ready")
        self._timer_hint.config(text="")
        self.window.lift()
        self.window.after(1500, lambda: self._show("setup"))

    def _update_display(self):
        """更新计时文字 + 进度弧"""
        can = self._ring_canvas_ref  # 引用最近的 canvas
        text = self._fmt(self.remaining)

        # 更新中心文字
        if hasattr(self, "_timer_label") and self._timer_label:
            can.itemconfig(self._timer_label, text=text)

        # 更新弧
        if self.total_seconds <= 0:
            return
        pct = (self.total_seconds - self.remaining) / self.total_seconds
        extent = -359 * pct
        color = T["sage"] if self.remaining == 0 else T["accent"]
        if hasattr(self, "_ring_arc") and self._ring_arc:
            can.itemconfig(self._ring_arc, extent=extent, outline=color)

    # ═══════════════════════════════════════
    #  第 3 页 · 历史
    # ═══════════════════════════════════════

    def _build_history(self):
        p = self.pages["history"]

        bar = tk.Frame(p, bg=T["bg"], height=36)
        bar.pack(fill="x", padx=24, pady=(28, 0))
        bar.pack_propagate(False)

        back = tk.Label(bar, text="←  返回", font=F["body"],
                        fg=T["dim"], bg=T["bg"], cursor="hand2")
        back.pack(side="left")
        back.bind("<Button-1>", lambda e: self._show("setup"))
        for ev in ["<Enter>", "<Leave>"]:
            back.bind(ev, lambda e, w=back, on=ev == "<Enter>":
                      w.config(fg=T["accent"] if on else T["dim"]))

        tk.Label(bar, text="历史记录", font=F["title"],
                 fg=T["text"], bg=T["bg"]).pack(side="left", padx=12)

        self._period = tk.StringVar(value="day")
        period_row = tk.Frame(bar, bg=T["bg"])
        period_row.pack(side="right")
        self._period_lbls = {}
        for lbl, val in [("日", "day"), ("周", "week"), ("月", "month")]:
            l = tk.Label(period_row, text=lbl, font=F["body"],
                         fg=T["dim"], bg=T["bg"], padx=8, cursor="hand2")
            l.pack(side="left")
            l.bind("<Button-1>", lambda e, v=val: self._on_period(v))
            self._period_lbls[val] = l

        self._hist_canvas = tk.Canvas(
            p, width=220, height=220,
            bg=T["bg"], highlightthickness=0, highlightbackground=T["bg"],
        )
        self._hist_canvas.pack(pady=(16, 4))

        self._legend_row = tk.Frame(p, bg=T["bg"])
        self._legend_row.pack()

        self._sessions_frame = tk.Frame(p, bg=T["bg"])
        self._sessions_frame.pack(fill="both", expand=True, padx=24, pady=(6, 14))

    def _on_period(self, val):
        self._period.set(val)
        for v, lbl in self._period_lbls.items():
            lbl.config(fg=T["accent"] if v == val else T["dim"])
        self._render_history()

    def _render_history(self):
        can = self._hist_canvas
        can.delete("all")

        for w in self._legend_row.winfo_children():
            w.destroy()
        for w in self._sessions_frame.winfo_children():
            w.destroy()

        period = self._period.get()
        now = datetime.now()

        if period == "day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        sessions = [s for s in self.history
                    if datetime.fromisoformat(s["date"]) >= start]

        if not sessions:
            can.create_text(110, 110, text="暂无记录",
                            font=F["body"], fill=T["dim"])
            tk.Label(self._sessions_frame,
                     text="完成一次专注后，记录会显示在这里",
                     font=F["caption"], fg=T["dim"], bg=T["bg"],
                     justify="center").pack(pady=(20, 0))
            return

        cat_map = {}
        for s in sessions:
            cat = s.get("category", "其他")
            cat_map[cat] = cat_map.get(cat, 0) + s["duration"]
        total = sum(cat_map.values())
        if total == 0:
            return

        items = sorted(cat_map.items(), key=lambda x: -x[1])

        cx, cy = 110, 110
        r_o, r_i = 90, 52
        angle = 90.0

        for i, (cat, dur) in enumerate(items):
            pct = dur / total
            ext = -359.0 * pct
            color = DONUT_COLORS[i % len(DONUT_COLORS)]
            can.create_arc(
                cx - r_o, cy - r_o, cx + r_o, cy + r_o,
                outline=color, width=r_o - r_i,
                style="arc", start=angle, extent=ext,
            )
            angle += ext

        can.create_text(cx, cy - 8, text=self._fmt_short(total),
                        font=F["number"], fill=T["text"])
        can.create_text(cx, cy + 14, text="总计",
                        font=F["small"], fill=T["dim"])

        for i, (cat, dur, pct, color) in enumerate(
            [(c, d, d / total, DONUT_COLORS[j % len(DONUT_COLORS)])
             for j, (c, d) in enumerate(items)]
        ):
            row = tk.Frame(self._legend_row, bg=T["bg"])
            row.pack(side="left", padx=8)
            tk.Label(row, text="●", font=("", 9),
                     fg=color, bg=T["bg"]).pack(side="left")
            tk.Label(row, text=f" {cat} {pct:.0%}",
                     font=F["small"], fg=T["dim"], bg=T["bg"]).pack(side="left")

        tk.Label(self._sessions_frame, text="最近记录",
                 font=F["small"], fg=T["dim"], bg=T["bg"], anchor="w").pack(
            fill="x", pady=(12, 4))

        scroll = tk.Frame(self._sessions_frame, bg=T["bg"])
        scroll.pack(fill="both", expand=True)

        for s in sorted(sessions, key=lambda x: x["date"], reverse=True)[:30]:
            line = tk.Frame(scroll, bg=T["bg"])
            line.pack(fill="x", pady=1)
            cat = s.get("category", "学习")
            dur = self._fmt(s["duration"])
            ts = datetime.fromisoformat(s["date"]).strftime("%m/%d  %H:%M")
            record_date = s["date"]  # 唯一标识

            tk.Label(line, text=cat, font=F["body"],
                     fg=T["text"], bg=T["bg"], anchor="w", width=10).pack(side="left")
            tk.Label(line, text=dur, font=F["number"],
                     fg=T["dim"], bg=T["bg"], anchor="e").pack(side="left", padx=(8, 0))
            tk.Label(line, text=ts, font=F["small"],
                     fg=T["dim"], bg=T["bg"], anchor="e").pack(side="left", padx=(8, 0))

            # 删除按钮
            del_btn = tk.Label(line, text="×", font=("Microsoft YaHei", 12, "bold"),
                               fg=T["dim"], bg=T["bg"], cursor="hand2",
                               padx=4)
            del_btn.pack(side="right")
            del_btn.bind("<Button-1>",
                         lambda e, d=record_date: self._delete_record(d))
            del_btn.bind("<Enter>", lambda e, w=del_btn: w.config(fg=T["danger"]))
            del_btn.bind("<Leave>", lambda e, w=del_btn: w.config(fg=T["dim"]))

    # ═══════════════════════════════════════
    #  共享
    # ═══════════════════════════════════════

    @staticmethod
    def _center_wheel_item(lb, idx, count, visible):
        """将选中项垂直居中于可见区域（对准横线指示器）"""
        half = visible // 2
        top = max(0, min(count - visible, idx - half))
        denom = count - visible
        lb.yview_moveto(top / denom if denom > 0 else 0)

    def _rounded_btn(self, parent, text, bg, fg, cmd, w, h):
        r = 12
        c = tk.Canvas(parent, width=w, height=h,
                      bg=T["bg"], highlightthickness=0, highlightbackground=T["bg"], cursor="hand2")
        c.create_oval(2, 2, 2 + 2 * r, 2 + 2 * r, fill=bg, outline="")
        c.create_oval(w - 2 - 2 * r, 2, w - 2, 2 + 2 * r, fill=bg, outline="")
        c.create_oval(2, h - 2 - 2 * r, 2 + 2 * r, h - 2, fill=bg, outline="")
        c.create_oval(w - 2 - 2 * r, h - 2 - 2 * r, w - 2, h - 2, fill=bg, outline="")
        c.create_rectangle(2 + r, 2, w - 2 - r, h - 2, fill=bg, outline="")
        c.create_rectangle(2, 2 + r, w - 2, h - 2 - r, fill=bg, outline="")
        c.create_text(w // 2, h // 2, text=text, font=F["body"], fill=fg)
        c.bind("<Button-1>", lambda e: cmd())
        return c

    # ═══════════════════════════════════════
    #  持久化
    # ═══════════════════════════════════════

    def _open_settings(self):
        """科目管理弹窗"""
        top = tk.Toplevel(self.window)
        top.title("科目管理")
        top.geometry("320x420")
        top.resizable(False, False)
        top.configure(bg=T["bg"])
        top.transient(self.window)
        top.grab_set()

        tk.Label(top, text="管理科目", font=F["title"],
                 fg=T["text"], bg=T["bg"]).pack(pady=(20, 4))
        tk.Label(top, text="添加或删除快捷科目",
                 font=F["caption"], fg=T["dim"], bg=T["bg"]).pack()

        # ── 新增区 ──
        add_frame = tk.Frame(top, bg=T["bg"])
        add_frame.pack(pady=(16, 8))

        new_var = tk.StringVar()
        tk.Entry(add_frame, textvariable=new_var, font=F["body"],
                 bg=T["surface"], fg=T["text"], relief="flat",
                 width=16, insertbackground=T["text"],
                 ).pack(side="left", ipady=4, padx=(0, 8))

        def do_add():
            val = new_var.get().strip()
            if val and val not in self.categories:
                self.categories.append(val)
                self._save_categories()
                new_var.set("")
                _refresh_list()
                self._rebuild_chips()

        tk.Button(add_frame, text="添加", font=F["caption"],
                  bg=T["accent"], fg=T["white"], relief="flat",
                  padx=12, pady=4, cursor="hand2",
                  command=do_add).pack(side="left")

        # ── 列表区 ──
        list_frame = tk.Frame(top, bg=T["bg"])
        list_frame.pack(fill="both", expand=True, padx=24, pady=(4, 12))

        canvas = tk.Canvas(list_frame, bg=T["bg"], highlightthickness=0,
                           highlightbackground=T["bg"])
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=T["bg"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _refresh_list():
            for w in inner.winfo_children():
                w.destroy()
            for cat in self.categories:
                row = tk.Frame(inner, bg=T["bg"])
                row.pack(fill="x", pady=1)
                tk.Label(row, text=cat, font=F["body"],
                         fg=T["text"], bg=T["bg"], anchor="w").pack(side="left")
                x = tk.Label(row, text="×", font=("Microsoft YaHei", 12, "bold"),
                             fg=T["dim"], bg=T["bg"], cursor="hand2", padx=6)
                x.pack(side="right")
                x.bind("<Button-1>", lambda e, c=cat: _delete_cat(c))
                x.bind("<Enter>", lambda e, w=x: w.config(fg=T["danger"]))
                x.bind("<Leave>", lambda e, w=x: w.config(fg=T["dim"]))

        def _delete_cat(cat):
            if len(self.categories) <= 1:
                return  # 至少保留一个
            self.categories.remove(cat)
            self._save_categories()
            _refresh_list()
            self._rebuild_chips()

        _refresh_list()

        # 关闭按钮
        tk.Button(top, text="关闭", font=F["body"],
                  bg=T["surface"], fg=T["text"], relief="flat",
                  padx=24, pady=6, cursor="hand2",
                  command=top.destroy).pack(pady=(0, 20))

    def _save_categories(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _rebuild_chips(self):
        """重新渲染设置页的科目 chips"""
        p = self.pages["setup"]
        # 找到 chip_row 并重建
        for child in p.winfo_children():
            if isinstance(child, tk.Frame) and child != p.winfo_children()[0]:
                # 遍历所有子组件找 chip_row
                pass
        # 简化：遍历 content frame 重建
        self._refresh_setup_chips()

    def _refresh_setup_chips(self):
        """销毁并重建设置页的科目 chip 行 + 齿轮"""
        p = self.pages["setup"]
        # bottom_bar (0), btn_bar (1), content (2)
        children = p.winfo_children()
        if len(children) >= 3:
            content = children[2]
            for c in content.winfo_children():
                if isinstance(c, tk.Frame) and c.winfo_children():
                    first_child = c.winfo_children()[0]
                    if isinstance(first_child, tk.Label):
                        txt = first_child.cget("text")
                        if txt in self.categories:
                            # chip_row found — rebuild
                            for w in c.winfo_children():
                                w.destroy()
                            for cat in self.categories[:6]:
                                self._chip(c, cat)
                            # 重建齿轮
                            gear = tk.Label(c, text=" ⚙", font=("Microsoft YaHei", 11),
                                            fg=T["dim"], bg=T["bg"], cursor="hand2")
                            gear.pack(side="left", padx=2)
                            gear.bind("<Button-1>", lambda e: self._open_settings())
                            gear.bind("<Enter>", lambda e, w=gear: w.config(fg=T["accent"]))
                            gear.bind("<Leave>", lambda e, w=gear: w.config(fg=T["dim"]))
                            return

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _delete_record(self, date_str):
        """删除一条历史记录并刷新"""
        self.history = [s for s in self.history if s.get("date") != date_str]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._render_history()

    def _save(self, category, duration):
        self.history.append({
            "category": category,
            "duration": duration,
            "date": datetime.now().isoformat(),
        })
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ═══════════════════════════════════════
    #  工具
    # ═══════════════════════════════════════

    @staticmethod
    def _fmt(sec):
        """hh:mm:ss 或 mm:ss"""
        s = int(sec)
        h = s // 3600
        m = (s % 3600) // 60
        ss = s % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{ss:02d}"
        return f"{m:02d}:{ss:02d}"

    @staticmethod
    def _fmt_short(sec):
        if sec >= 3600:
            return f"{int(sec // 3600)}时{int((sec % 3600) // 60)}分"
        if sec >= 60:
            return f"{int(sec // 60)}分"
        return f"{int(sec)}秒"

    def _play_beep(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

    def _on_close(self):
        if self.after_id:
            self.window.after_cancel(self.after_id)
        self.window.destroy()


if __name__ == "__main__":
    FocusApp().window.mainloop()
