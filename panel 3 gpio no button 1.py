import tkinter as tk
from tkinter import ttk

# ======================================================
# GPIO SUPPORT (with fallback so it runs on Windows)
# ======================================================
try:
    import RPi.GPIO as GPIO
    _HAS_GPIO = True
except ImportError:
    _HAS_GPIO = False

    class _DummyGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0

        def setwarnings(self, flag):
            pass

        def setmode(self, mode):
            print(f"[DUMMY GPIO] setmode({mode})")

        def setup(self, pin, mode):
            print(f"[DUMMY GPIO] setup(pin={pin}, mode={mode})")

        def output(self, pin, value):
            print(f"[DUMMY GPIO] output(pin={pin}, value={value})")

        def input(self, pin):
            print(f"[DUMMY GPIO] input(pin={pin}) -> LOW")
            return self.LOW

        def cleanup(self):
            print("[DUMMY GPIO] cleanup()")

    GPIO = _DummyGPIO()  # type: ignore


# ======================================================
# PIN MAPPING
# (logical pin ↔ BCM GPIO ↔ physical pin on Pi 3 A+)
#
# NOTE: Logical pin numbers are from your circuit.
#       BCM and physical pins can be changed if needed.
# ======================================================

# -------- COMMON PINS USED FOR BUTTON 3..7 MUX AND LED COMMON --------
# Logical pin 1  (COMMON_1_PIN):
#   - Meaning: common input for all LEDs, and "ON" source for BTN 3..7
#   - BCM 17  → physical pin 11
COMMON_1_PIN = 17

# Logical pin 3  (COMMON_3_PIN):
#   - Meaning: "OFF" source for BTN 3..7 (when buttons are OFF, outputs follow this)
#   - BCM 27  → physical pin 13
COMMON_3_PIN = 27

# -------- BUTTON 2 INPUT + ITS EXTRA OUTPUTS --------
# Logical pin 17 (PIN17_IN):
#   - Input for BTN 2 logic
#   - BCM 18 → physical pin 12
PIN17_IN = 18

# Logical pin 18 (PIN18_OUT):
#   - Output whose state should equal logical pin 17 WHILE BTN 2 is PRESSED
#   - BCM 25 → physical pin 22
PIN18_OUT = 25

# Logical "150 C2 xp3" (PIN150_OUT):
#   - Extra output driven when BTN 2 is pressed, same level as logical 17
#   - BCM 22 → physical pin 15
PIN150_OUT = 22

# Logical "11 B8 xp2" (PIN11_OUT):
#   - Extra output driven when BTN 2 is pressed, same level as logical 17
#   - BCM 24 → physical pin 18
PIN11_OUT = 24

# All extra BTN 2 outputs (no "main" BTN 2 output pin):
BTN2_EXTRA_OUTPUTS = [PIN150_OUT, PIN11_OUT, PIN18_OUT]

# -------- BUTTON OUTPUT PINS FOR BTN 3..7 (MUXED BY PIN 1 / PIN 3) --------
# BTN 1:
#   - Per your latest logic: NO logical or physical pin is attached.
#   - It is only a GUI control (no GPIO).
#
# BTN 2:
#   - Per your latest logic: NO main output pin.
#   - Only the extra outputs above are used.

# BTN 3..7 outputs:
#   When a button is OFF → its output equals logical pin 3 (COMMON_3_PIN)
#   When a button is ON  → its output equals logical pin 1 (COMMON_1_PIN)

# BTN 3 output:
#   - Logical net: "23 B10 xp3"
#   - BCM 23 → physical pin 16
# BTN 4 output:
#   - Logical net: "9 C9 xp2"
#   - BCM 9  → physical pin 21
# BTN 5 output:
#   - Logical net: "20 C4 xp3"
#   - BCM 20 → physical pin 38
# BTN 6 output:
#   - Logical net: "14 B9 xp2"
#   - BCM 14 → physical pin 8
# BTN 7 output:
#   - Logical net: "15 A9 xp2"
#   - BCM 15 → physical pin 10
BUTTON_GPIO_PINS = {
    3: 23,
    4: 9,
    5: 20,
    6: 14,
    7: 15,
}


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

        self.button_states = {}   # logical states for BTN 1..7 (True = ON)
        self.button_widgets = {}  # mapping id -> tk.Button
        self.default_button_bg = None

        self.init_gpio()
        self.build_ui()

        parent.protocol("WM_DELETE_WINDOW", self.on_close)

    # ======================================================
    # GPIO INITIALIZATION
    # ======================================================
    def init_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Common pins as inputs (driven by your external circuit)
        GPIO.setup(COMMON_1_PIN, GPIO.IN)
        GPIO.setup(COMMON_3_PIN, GPIO.IN)

        # BTN 2 input: logical pin 17
        GPIO.setup(PIN17_IN, GPIO.IN)

        # BTN 2 extra outputs: logical 18, "150 C2 xp3", "11 B8 xp2"
        for p in BTN2_EXTRA_OUTPUTS:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.LOW)

        # Button outputs for BTN 3..7 (muxed between logical 1 and logical 3)
        for btn_id, pin in BUTTON_GPIO_PINS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        # Initial muxed outputs for BTN 3..7 (start as OFF → follow logical pin 3)
        self.update_muxed_outputs()

        # Periodically keep muxed outputs in sync with COMMON pins
        self.after(100, self.periodic_mux_update)

    def periodic_mux_update(self):
        """Keep BTN 3..7 outputs following COMMON_1_PIN / COMMON_3_PIN."""
        self.update_muxed_outputs()
        self.after(100, self.periodic_mux_update)

    def update_muxed_outputs(self):
        """For BTN 3..7, drive outputs equal to COMMON_1_PIN (ON) or COMMON_3_PIN (OFF)."""
        common1_level = GPIO.input(COMMON_1_PIN)
        common3_level = GPIO.input(COMMON_3_PIN)

        for btn_id in range(3, 8):  # BTN 3..7
            pin = BUTTON_GPIO_PINS.get(btn_id)
            if pin is None:
                continue
            use_common1 = self.button_states.get(btn_id, False)
            level = common1_level if use_common1 else common3_level
            GPIO.output(pin, level)

    def set_button_gpio(self, btn_id, on):
        """
        Drive the physical GPIO pins according to all current logic.

        - BTN 1: GUI-only, no GPIO.
        - BTN 2: no main output; only extra outputs (150, 11, 18).
        - BTN 3..7: mux between logical pin 1 and logical pin 3.
        """
        # BTN 3..7: muxed between COMMON_1_PIN / COMMON_3_PIN
        if 3 <= btn_id <= 7:
            self.update_muxed_outputs()
            return

        # BTN 2: uses only extra outputs, no main output pin
        if btn_id == 2:
            if on:
                # Read logical pin 17 and copy its state to 150, 11, and 18
                src_level = GPIO.input(PIN17_IN)
                for p in BTN2_EXTRA_OUTPUTS:
                    GPIO.output(p, src_level)
            else:
                # When BTN 2 is released, those outputs go LOW
                for p in BTN2_EXTRA_OUTPUTS:
                    GPIO.output(p, GPIO.LOW)
            return

        # BTN 1: no GPIO attached (GUI-only toggle)
        if btn_id == 1:
            return

    # ======================================================
    # UI BUILD
    # ======================================================
    def build_ui(self):
        BTN_W, BTN_H = 10, 2

        main = ttk.Frame(self)
        main.pack(fill="x")

        left = ttk.Frame(main)
        left.pack(side="left", expand=True, padx=40, pady=40)

        right = ttk.Frame(main)
        right.pack(side="right", padx=20, pady=40)

        # -------------------------
        # BUTTON GRID + LED LAYOUT
        # -------------------------
        btn_grid = ttk.Frame(left)
        btn_grid.pack(pady=(10, 0))

        names_stack = ["ACS", "CPLR", "PWR CV 1", "PWR CV 2", "PWR CV 3"]

        LED_SIZE = 28
        SPACER_H = LED_SIZE

        # Top row: BTN 1..4 with alignment
        self.top_buttons = []
        for i in range(4):
            col = ttk.Frame(btn_grid)
            col.grid(row=0, column=i, padx=22)

            inner = ttk.Frame(col)
            inner.pack()

            if i in (0, 1):
                # LED above BTN 1 and BTN 2
                led_frame = ttk.Frame(inner)
                led_frame.grid(row=0, column=0, pady=(0, 0))
                canvas, led = create_led(led_frame, size=LED_SIZE)
                canvas.pack()
            else:
                # Spacer for BTN 3 and BTN 4 to align with LEDs of BTN 1 and BTN 2
                real_bg = ttk.Style().lookup("TFrame", "background")
                spacer = tk.Canvas(
                    inner,
                    width=LED_SIZE,
                    height=SPACER_H,
                    highlightthickness=0,
                    bg=real_bg
                )
                spacer.grid(row=0, column=0)

            btn_id = i + 1
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

        # Second row: BTN 5..7 under first three
        self.bottom_buttons = []
        for i in range(3):
            col = ttk.Frame(btn_grid)
            col.grid(row=1, column=i, padx=22, pady=(18, 0))

            btn_id = 4 + i + 1  # BTN 5..7
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

        # LED 1 under BTN 4
        led1_col = ttk.Frame(btn_grid)
        led1_col.grid(row=1, column=3, padx=22, pady=(18, 0), sticky="n")

        led1_frame = ttk.Frame(led1_col)
        led1_frame.pack()
        canvas1, led1 = create_led(led1_frame, size=28)
        canvas1.pack()
        ttk.Label(led1_frame, text="1").pack(pady=(2, 0))

        # Vertical stack LEDs (ACS, CPLR, PWR CV 1..3)
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

        # "DATA CV" label under LED 1 and LED 2
        data_cv_frame = ttk.Frame(btn_grid)
        data_cv_frame.grid(row=2, column=3, columnspan=2, pady=(2, 0))
        ttk.Label(
            data_cv_frame,
            text="DATA CV",
            font=("Arial", 9, "bold")
        ).pack()

        # Right-hand log area
        ttk.Label(
            right,
            text="PANEL 3 LOG",
            font=("Arial", 11, "bold")
        ).pack()
        self.log = tk.Text(right, width=32, height=18)
        self.log.pack()

    # ======================================================
    # BUTTON LOGIC
    # ======================================================
    def set_button_visual(self, btn_id, on):
        btn = self.button_widgets[btn_id]
        if on:
            btn.config(bg="green", fg="white", activebackground="green")
        else:
            btn.config(bg=self.default_button_bg, fg="black")

    def on_button_click(self, btn_id):
        if btn_id == 2:
            # BTN 2 is momentary: ON for 500 ms, then OFF automatically.
            if not self.button_states[2]:
                self.button_states[2] = True
                self.set_button_visual(2, True)
                self.set_button_gpio(2, True)
                self.log_event("BTN 2 turned ON")
                self.after(500, self.auto_turn_off_btn2)
        else:
            # BTN 1 and BTN 3..7: simple toggle of state
            new_state = not self.button_states[btn_id]
            self.button_states[btn_id] = new_state
            self.set_button_visual(btn_id, new_state)
            self.set_button_gpio(btn_id, new_state)
            self.log_event(f"BTN {btn_id} turned {'ON' if new_state else 'OFF'}")

    def auto_turn_off_btn2(self):
        if self.button_states.get(2):
            self.button_states[2] = False
            self.set_button_visual(2, False)
            self.set_button_gpio(2, False)
            self.log_event("BTN 2 turned OFF (auto)")

    # ======================================================
    # LOGGING & CLEANUP
    # ======================================================
    def log_event(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def on_close(self):
        try:
            GPIO.cleanup()
        except Exception:
            pass
        self.winfo_toplevel().destroy()


if __name__ == "__main__":
    root = tk.Tk()
    Panel3(root)
    root.mainloop()
