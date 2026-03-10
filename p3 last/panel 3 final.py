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

# -------- BUTTON 1 & 2 INPUT + BTN 2 EXTRA OUTPUTS --------
# Logical pin 17 (PIN17_IN):
#   - Input for BTN 1 and BTN 2 logic
#   - BCM 18 → physical pin 12
PIN17_IN = 18

# Logical pin 18 (PIN18_OUT):
#   - Output whose state should equal logical pin 17 WHILE BTN 2 is PRESSED
#   - Also used when BTN 1 is OFF (18 follows 17, 100 forced LOW)
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

# Logical "100 ???" (PIN100_OUT):
#   - Output driven when BTN 1 is ON, same level as logical 17
#   - BCM 21 → physical pin 40
PIN100_OUT = 21

# All extra BTN 2 outputs (no "main" BTN 2 output pin):
BTN2_EXTRA_OUTPUTS = [PIN150_OUT, PIN11_OUT, PIN18_OUT]

# -------- BUTTON OUTPUT PINS FOR BTN 3..7 (MUXED BY PIN 1 / PIN 3) --------
# BTN 3 output: "23 B10 xp3"  → BCM 23 → physical 16
# BTN 4 output: "9 C9 xp2"    → BCM 9  → physical 21
# BTN 5 output: "20 C4 xp3"   → BCM 20 → physical 38
# BTN 6 output: "14 B9 xp2"   → BCM 14 → physical 8
# BTN 7 output: "15 A9 xp2"   → BCM 15 → physical 10
BUTTON_GPIO_PINS = {
    3: 23,
    4: 9,
    5: 20,
    6: 14,
    7: 15,
}

# ======================================================
# LED SINK PINS (all LEDs share common input logical pin 1)
#
# Each LED has:
#   - Common/anode: logical pin 1 (COMMON_1_PIN, BCM 17, phys 11)
#   - Sinks through its own logical pin N (configured as GPIO.IN,
#     driven LOW by your external circuit when LED should glow).
#
# LED is ON when:
#   COMMON_1_PIN is HIGH  AND  sink pin is LOW (grounded).
# ======================================================

# LED above BTN 1:
#   - Logical sink pin 7 → LED1_SINK_PIN
#   - BCM 5 → physical pin 29
LED1_SINK_PIN = 5

# LED above BTN 2:
#   - Logical sink pin 8 → LED2_SINK_PIN
#   - BCM 6 → physical pin 31
LED2_SINK_PIN = 6

# LED under BTN 4 (DATA CV, label "1"):
#   - Logical sink pin 15 → DATA_CV1_SINK_PIN
#   - BCM 2 → physical pin 3
DATA_CV1_SINK_PIN = 2

# LED to the right, under the stack (label "2"):
#   - Logical sink pin 16 → DATA_CV2_SINK_PIN
#   - BCM 3 → physical pin 5
DATA_CV2_SINK_PIN = 3

# ACS_LED (label "ACS"):
#   - Logical sink pin 9 → ACS_SINK_PIN
#   - BCM 12 → physical pin 32
ACS_SINK_PIN = 12

# CPLR_LED (label "CPLR"):
#   - Logical sink pin 10 → CPLR_SINK_PIN
#   - BCM 13 → physical pin 33
CPLR_SINK_PIN = 13

# PWR_CV1_LED (label "PWR CV 1"):
#   - Logical sink pin 11 → PWR_CV1_SINK_PIN
#   - BCM 16 → physical pin 36
PWR_CV1_SINK_PIN = 16

# PWR_CV2_LED (label "PWR CV 2"):
#   - Logical sink pin 12 → PWR_CV2_SINK_PIN
#   - BCM 19 → physical pin 35
PWR_CV2_SINK_PIN = 19

# PWR_CV3_LED (label "PWR CV 3"):
#   - Logical sink pin 13 → PWR_CV3_SINK_PIN
#   - BCM 26 → physical pin 37
PWR_CV3_SINK_PIN = 26

# ======================================================
# BUTTON LABELS (GUI text only, logic unchanged)
# ======================================================
BUTTON_LABELS = {
    1: "ACS PWR",
    2: "0-ACS",
    3: "BIT",
    4: "TEST",
    5: "DA HEAT OUT",
    6: "L.G.UP SIM",
    7: "TRAING",
}


def create_led(parent, size=22, color="gray"):
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        highlightthickness=0,
        bg="#d9d9d9"
    )
    led = canvas.create_oval(
        2, 2, size - 2, size - 2,
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
        self.pack(fill="both", expand=True, padx=6, pady=6)

        self.button_states = {}   # logical states for BTN 1..7 (True = ON)
        self.button_widgets = {}  # mapping id -> tk.Button
        self.default_button_bg = None

        # LED widget references
        self.led_btn1_canvas = None
        self.led_btn1 = None
        self.led_btn2_canvas = None
        self.led_btn2 = None

        self.led_data_cv1_canvas = None   # LED under BTN 4 ("1")
        self.led_data_cv1 = None
        self.led_data_cv2_canvas = None   # LED on right, label "2"
        self.led_data_cv2 = None

        self.led_acs_canvas = None
        self.led_acs = None
        self.led_cplr_canvas = None
        self.led_cplr = None
        self.led_pwr_cv1_canvas = None
        self.led_pwr_cv1 = None
        self.led_pwr_cv2_canvas = None
        self.led_pwr_cv2 = None
        self.led_pwr_cv3_canvas = None
        self.led_pwr_cv3 = None

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

        # BTN 1 / BTN 2 input: logical pin 17
        GPIO.setup(PIN17_IN, GPIO.IN)

        # BTN 2 extra outputs: logical 18, "150 C2 xp3", "11 B8 xp2"
        for p in BTN2_EXTRA_OUTPUTS:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.LOW)

        # BTN 1 extra output: logical 100
        GPIO.setup(PIN100_OUT, GPIO.OUT)
        GPIO.output(PIN100_OUT, GPIO.LOW)

        # Button outputs for BTN 3..7 (muxed between logical 1 and logical 3)
        for btn_id, pin in BUTTON_GPIO_PINS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        # LED sink pins as inputs (external circuit pulls LOW to turn LED ON)
        sink_pins = [
            LED1_SINK_PIN,
            LED2_SINK_PIN,
            DATA_CV1_SINK_PIN,
            DATA_CV2_SINK_PIN,
            ACS_SINK_PIN,
            CPLR_SINK_PIN,
            PWR_CV1_SINK_PIN,
            PWR_CV2_SINK_PIN,
            PWR_CV3_SINK_PIN,
        ]
        for p in sink_pins:
            GPIO.setup(p, GPIO.IN)

        # Initial muxed outputs and LEDs
        self.update_muxed_outputs()
        self.update_leds()

        # Periodically keep muxed outputs and LEDs in sync with GPIO pins
        self.after(100, self.periodic_update)

    def periodic_update(self):
        """Keep BTN 3..7 outputs and LED indicators in sync with GPIO inputs."""
        self.update_muxed_outputs()
        self.update_leds()
        self.after(100, self.periodic_update)

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

    def update_leds(self):
        """
        Update all GUI LEDs based on GPIO levels.

        Condition for each LED to be ON:
            COMMON_1_PIN (logical 1) is HIGH
            AND that LED's sink logical pin is LOW (grounded).
        """
        if self.led_btn1_canvas is None:
            return  # UI not yet built

        common1_level = GPIO.input(COMMON_1_PIN)

        def is_on(sink_pin):
            return (common1_level == GPIO.HIGH) and (GPIO.input(sink_pin) == GPIO.LOW)

        # LED above BTN 1 (logical 7)
        if self.led_btn1_canvas is not None:
            self.set_indicator_led(self.led_btn1_canvas, self.led_btn1, is_on(LED1_SINK_PIN))

        # LED above BTN 2 (logical 8)
        if self.led_btn2_canvas is not None:
            self.set_indicator_led(self.led_btn2_canvas, self.led_btn2, is_on(LED2_SINK_PIN))

        # LED under BTN 4, label "1" (logical 15)
        if self.led_data_cv1_canvas is not None:
            self.set_indicator_led(
                self.led_data_cv1_canvas, self.led_data_cv1, is_on(DATA_CV1_SINK_PIN)
            )

        # LED to the right, label "2" (logical 16)
        if self.led_data_cv2_canvas is not None:
            self.set_indicator_led(
                self.led_data_cv2_canvas, self.led_data_cv2, is_on(DATA_CV2_SINK_PIN)
            )

        # ACS, CPLR, PWR CV 1..3 (logical 9..13)
        if self.led_acs_canvas is not None:
            self.set_indicator_led(self.led_acs_canvas, self.led_acs, is_on(ACS_SINK_PIN))

        if self.led_cplr_canvas is not None:
            self.set_indicator_led(
                self.led_cplr_canvas, self.led_cplr, is_on(CPLR_SINK_PIN)
            )

        if self.led_pwr_cv1_canvas is not None:
            self.set_indicator_led(
                self.led_pwr_cv1_canvas, self.led_pwr_cv1, is_on(PWR_CV1_SINK_PIN)
            )

        if self.led_pwr_cv2_canvas is not None:
            self.set_indicator_led(
                self.led_pwr_cv2_canvas, self.led_pwr_cv2, is_on(PWR_CV2_SINK_PIN)
            )

        if self.led_pwr_cv3_canvas is not None:
            self.set_indicator_led(
                self.led_pwr_cv3_canvas, self.led_pwr_cv3, is_on(PWR_CV3_SINK_PIN)
            )

    # ======================================================
    # UI BUILD
    # ======================================================
    def build_ui(self):
        BTN_W, BTN_H = 9, 2   # reduced width; height kept at 2

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", padx=4, pady=4)

        right = ttk.Frame(main)
        right.pack(side="right", padx=4, pady=4, fill="both", expand=True)

        # -------------------------
        # BUTTON GRID + LED LAYOUT
        # -------------------------
        btn_grid = ttk.Frame(left)
        btn_grid.pack(pady=(4, 0))

        names_stack = ["ACS", "CPLR", "PWR CV 1", "PWR CV 2", "PWR CV 3"]

        LED_SIZE = 22
        SPACER_H = LED_SIZE

        # Top row: BTN 1..4 with alignment
        self.top_buttons = []
        for i in range(4):
            col = ttk.Frame(btn_grid)
            col.grid(row=0, column=i, padx=6)

            inner = ttk.Frame(col)
            inner.pack()

            if i in (0, 1):
                # LED above BTN 1 and BTN 2
                led_frame = ttk.Frame(inner)
                led_frame.grid(row=0, column=0, pady=(0, 0))
                canvas, led = create_led(led_frame, size=LED_SIZE)
                canvas.pack()

                if i == 0:
                    self.led_btn1_canvas = canvas
                    self.led_btn1 = led
                else:
                    self.led_btn2_canvas = canvas
                    self.led_btn2 = led
            else:
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
            btn_text = BUTTON_LABELS.get(btn_id, f"BTN {btn_id}")
            btn = tk.Button(
                inner,
                text=btn_text,
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
            col.grid(row=1, column=i, padx=6, pady=(10, 0))

            btn_id = 4 + i + 1  # BTN 5..7
            btn_text = BUTTON_LABELS.get(btn_id, f"BTN {btn_id}")
            btn = tk.Button(
                col,
                text=btn_text,
                width=BTN_W,
                height=BTN_H,
                command=lambda bid=btn_id: self.on_button_click(bid)
            )
            btn.pack()
            self.bottom_buttons.append(btn)

            self.button_widgets[btn_id] = btn
            self.button_states[btn_id] = False

        # LED under BTN 4 (DATA CV LED 1, label "1")
        led1_col = ttk.Frame(btn_grid)
        led1_col.grid(row=1, column=3, padx=6, pady=(10, 0), sticky="n")

        led1_frame = ttk.Frame(led1_col)
        led1_frame.pack()
        canvas1, led1 = create_led(led1_frame, size=LED_SIZE)
        canvas1.pack()
        ttk.Label(led1_frame, text="1").pack(pady=(1, 0))

        self.led_data_cv1_canvas = canvas1
        self.led_data_cv1 = led1

        # Vertical stack LEDs (ACS, CPLR, PWR CV 1..3)
        stack_col = ttk.Frame(btn_grid)
        stack_col.grid(row=0, column=4, padx=(6, 0), sticky="n")

        for name in names_stack:
            f = ttk.Frame(stack_col)
            f.pack(pady=1)
            c, l = create_led(f, size=LED_SIZE)
            c.pack()
            ttk.Label(f, text=name, font=("Arial", 7)).pack()

            if name == "ACS":
                self.led_acs_canvas = c
                self.led_acs = l
            elif name == "CPLR":
                self.led_cplr_canvas = c
                self.led_cplr = l
            elif name == "PWR CV 1":
                self.led_pwr_cv1_canvas = c
                self.led_pwr_cv1 = l
            elif name == "PWR CV 2":
                self.led_pwr_cv2_canvas = c
                self.led_pwr_cv2 = l
            elif name == "PWR CV 3":
                self.led_pwr_cv3_canvas = c
                self.led_pwr_cv3 = l

        # LED 2 (DATA CV LED 2, label "2")
        led2_col = ttk.Frame(btn_grid)
        led2_col.grid(row=1, column=4, padx=(6, 0), pady=(10, 0), sticky="n")

        led2_frame = ttk.Frame(led2_col)
        led2_frame.pack()
        canvas2, led2 = create_led(led2_frame, size=LED_SIZE)
        canvas2.pack()
        ttk.Label(led2_frame, text="2").pack(pady=(1, 0))

        self.led_data_cv2_canvas = canvas2
        self.led_data_cv2 = led2

        # "DATA CV" label under LED 1 and LED 2
        data_cv_frame = ttk.Frame(btn_grid)
        data_cv_frame.grid(row=2, column=3, columnspan=2, pady=(2, 0))
        ttk.Label(
            data_cv_frame,
            text="DATA CV",
            font=("Arial", 8, "bold")
        ).pack()

        # vertical letters column
        stack_col2 = ttk.Frame(btn_grid)
        stack_col2.grid(row=0, column=5, padx=(6, 0), sticky="n")

        for text1 in ["O", "p", "r", "n", "l"]:
            f = ttk.Frame(stack_col2)
            f.pack(pady=10)
            ttk.Label(f, text=text1, font=("Arial", 9)).pack()

        # Right-hand log area
        ttk.Label(
            right,
            text="PANEL 3 LOG",
            font=("Arial", 10, "bold")
        ).pack(anchor="w")

        self.log = tk.Text(right, width=22, height=20, font=("Arial", 8))
        self.log.pack(fill="both", expand=True)

    # ======================================================
    # BUTTON LOGIC
    # ======================================================
    def set_button_visual(self, btn_id, on):
        btn = self.button_widgets[btn_id]
        if on:
            btn.config(bg="green", fg="white", activebackground="green")
        else:
            btn.config(bg=self.default_button_bg, fg="black")

    def set_indicator_led(self, canvas, led_item, on):
        """Set a round indicator LED fill color."""
        color = "green" if on else "gray"
        canvas.itemconfig(led_item, fill=color)

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

    def set_button_gpio(self, btn_id, on):
        """
        Drive the physical GPIO pins according to all current logic.

        - BTN 1:
            input  = logical 17
            OFF    -> logical 18 follows 17, logical 100 is LOW
            ON     -> logical 100 follows 17 (18 unchanged here)
        - BTN 2: no main output; only extra outputs (150, 11, 18).
        - BTN 3..7: mux between logical pin 1 and logical pin 3.
        """

        # BTN 1: route logical 17 to 18 (OFF) or 100 (ON)
        if btn_id == 1:
            src_level = GPIO.input(PIN17_IN)
            if on:
                # BTN 1 ON: 100 == 17
                GPIO.output(PIN100_OUT, src_level)
            else:
                # BTN 1 OFF: 18 == 17, 100 forced LOW
                GPIO.output(PIN100_OUT, GPIO.LOW)
                GPIO.output(PIN18_OUT, src_level)
            return

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
