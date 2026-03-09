import tkinter as tk
from tkinter import ttk


def create_led(parent, size=30, color="gray"):
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        highlightthickness=0,
        bg="#d9d9d9"
    )
    led = canvas.create_oval(
        3, 3, size - 3, size - 3,
        fill=color,
        outline="black"
    )
    return canvas, led


class Panel3(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        parent.title("Panel 3 — HMI")
        parent.geometry("800x480")
        parent.resizable(False, False)
        self.pack(fill="both", expand=True, padx=10, pady=10)

        self.button_states = {}
        self.button_widgets = {}
        self.default_button_bg = None

        self.build_ui()

    def build_ui(self):
        BTN_W, BTN_H = 10, 2

        main = ttk.Frame(self)
        main.pack(fill="x")

        left = ttk.Frame(main)
        left.pack(side="left", expand=True, padx=40, pady=40)

        right = ttk.Frame(main)
        right.pack(side="right", padx=20, pady=40)

        # =========================
        # BUTTON GRID + LED LAYOUT
        # =========================
        btn_grid = ttk.Frame(left)
        btn_grid.pack(pady=(10, 0))

        names_stack = ["ACS", "CPLR", "PWR CV 1", "PWR CV 2", "PWR CV 3"]

        # ---------- TOP ROW: 4 BUTTONS (ALL PERFECTLY ALIGNED) ----------
        # Key fix: every column (0-3) gets the SAME two-row inner structure:
        #   row=0 → LED canvas OR a same-size invisible spacer canvas
        #   row=1 → the button
        # This guarantees all four buttons land on the exact same pixel row.

        LED_SIZE = 28
        SPACER_H = LED_SIZE   # spacer matches LED canvas height exactly

        self.top_buttons = []
        for i in range(4):
            col = ttk.Frame(btn_grid)
            col.grid(row=0, column=i, padx=22)

            inner = ttk.Frame(col)
            inner.pack()

            if i in (0, 1):
                # Real LED above button
                led_frame = ttk.Frame(inner)
                led_frame.grid(row=0, column=0, pady=(0, 0))
                canvas, led = create_led(led_frame, size=LED_SIZE)
                canvas.pack()
            else:
                # Invisible spacer — same height as the LED canvas so BTN 3 & 4
                # are pushed down by exactly the same amount as BTN 1 & 2.
                # Query the real ttk frame bg at runtime so it matches on every OS/theme.
                real_bg = ttk.Style().lookup("TFrame", "background")
                spacer = tk.Canvas(
                    inner,
                    width=LED_SIZE,
                    height=SPACER_H,
                    highlightthickness=0,
                    bg=real_bg
                )
                spacer.grid(row=0, column=0)

            btn_id = i + 1              # BTN 1..4
            btn = tk.Button(
                inner,
                text=f"BTN {btn_id}",
                width=BTN_W,
                height=BTN_H,
                command=lambda bid=btn_id: self.on_button_click(bid)
            )
            btn.grid(row=1, column=0)
            self.top_buttons.append(btn)

            if self.default_button_bg is None:
                self.default_button_bg = btn.cget("bg")
            self.button_widgets[btn_id] = btn
            self.button_states[btn_id] = False

        # ---------- SECOND ROW: 3 BUTTONS UNDER FIRST THREE ----------
        self.bottom_buttons = []
        for i in range(3):
            col = ttk.Frame(btn_grid)
            col.grid(row=1, column=i, padx=22, pady=(18, 0))

            btn_id = 4 + i + 1          # BTN 5..7
            btn = tk.Button(
                col,
                text=f"BTN {btn_id}",
                width=BTN_W,
                height=BTN_H,
                command=lambda bid=btn_id: self.on_button_click(bid)
            )
            btn.pack()
            self.bottom_buttons.append(btn)

            self.button_widgets[btn_id] = btn
            self.button_states[btn_id] = False

        # ---------- UNDER BTN 4: LED 1 ----------
        led1_col = ttk.Frame(btn_grid)
        led1_col.grid(row=1, column=3, padx=22, pady=(18, 0), sticky="n")

        led1_frame = ttk.Frame(led1_col)
        led1_frame.pack()
        canvas1, led1 = create_led(led1_frame, size=28)
        canvas1.pack()
        ttk.Label(led1_frame, text="1").pack(pady=(2, 0))

        # ---------- RIGHT OF BTN 4: STACKED LEDs ----------
        stack_col = ttk.Frame(btn_grid)
        stack_col.grid(row=0, column=4, padx=(10, 0), sticky="n")

        for name in names_stack:
            f = ttk.Frame(stack_col)
            f.pack(pady=2)
            c, l = create_led(f, size=28)
            c.pack()
            ttk.Label(f, text=name, font=("Arial", 8)).pack()

        # LED 2
        led2_col = ttk.Frame(btn_grid)
        led2_col.grid(row=1, column=4, padx=(10, 0), pady=(18, 0), sticky="n")

        led2_frame = ttk.Frame(led2_col)
        led2_frame.pack()
        canvas2, led2 = create_led(led2_frame, size=28)
        canvas2.pack()
        ttk.Label(led2_frame, text="2").pack(pady=(2, 0))

        # ---------- "DATA CV" COMBINED LABEL SPANNING LED 1 AND LED 2 ----------
        data_cv_frame = ttk.Frame(btn_grid)
        data_cv_frame.grid(row=2, column=3, columnspan=2, pady=(2, 0))
        ttk.Label(
            data_cv_frame,
            text="DATA CV",
            font=("Arial", 9, "bold")
        ).pack()

        # =========================
        # SIMPLE LOG AREA ON RIGHT
        # =========================
        ttk.Label(
            right,
            text="PANEL 3 LOG",
            font=("Arial", 11, "bold")
        ).pack()
        self.log = tk.Text(right, width=32, height=18)
        self.log.pack()

    # ---------- BUTTON LOGIC ----------

    def set_button_visual(self, btn_id, on):
        btn = self.button_widgets[btn_id]
        if on:
            btn.config(bg="green", fg="white", activebackground="green")
        else:
            btn.config(bg=self.default_button_bg, fg="black")

    def on_button_click(self, btn_id):
        if btn_id == 2:
            if not self.button_states[2]:
                self.button_states[2] = True
                self.set_button_visual(2, True)
                self.log_event("BTN 2 turned ON")
                self.after(500, self.auto_turn_off_btn2)
        else:
            new_state = not self.button_states[btn_id]
            self.button_states[btn_id] = new_state
            self.set_button_visual(btn_id, new_state)
            self.log_event(f"BTN {btn_id} turned {'ON' if new_state else 'OFF'}")

    def auto_turn_off_btn2(self):
        if self.button_states.get(2):
            self.button_states[2] = False
            self.set_button_visual(2, False)
            self.log_event("BTN 2 turned OFF (auto)")

    # ---------- LOGGING ----------

    def log_event(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")


if __name__ == "__main__":
    root = tk.Tk()
    Panel3(root)
    root.mainloop()
