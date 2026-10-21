# app/relay.py
class Relay:
    """Pump relay. Default OFF. Falls back to simulation when not on a Raspberry Pi.
    Many relay boards are ACTIVE-LOW. Check yours and set active_high=False if needed."""
    def __init__(self, pin=17):
        self.on, self.dev = False, None
        try:
            from gpiozero import OutputDevice
            self.dev = OutputDevice(pin, active_high=True, initial_value=False)
        except Exception:
            pass

    @property
    def simulated(self):
        return self.dev is None

    def set(self, on: bool):
        self.on = on
        if self.dev:
            self.dev.on() if on else self.dev.off()