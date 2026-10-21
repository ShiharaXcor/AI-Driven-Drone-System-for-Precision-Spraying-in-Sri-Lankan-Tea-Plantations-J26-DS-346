# app/gps.py
import os, random


class GPS:
    """u-blox NEO-M8N over serial if GPS_PORT is set (for example COM5 or /dev/serial0),
    otherwise a simulated slow drift so the dashboard map can be tested."""
    def __init__(self):
        self.lat = float(os.getenv("GPS_START_LAT", "7.4863"))
        self.lon = float(os.getenv("GPS_START_LON", "80.3647"))
        self.ser = None
        port = os.getenv("GPS_PORT")
        if port:
            import serial
            self.ser = serial.Serial(port, 9600, timeout=1)

    def read(self):
        if self.ser:
            import pynmea2
            for _ in range(20):
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if line.startswith(("$GPGGA", "$GNGGA")):
                    try:
                        m = pynmea2.parse(line)
                        if m.latitude:
                            return {"lat": m.latitude, "lon": m.longitude, "alt": float(m.altitude or 0),
                                    "sats": int(m.num_sats or 0), "hdop": float(m.horizontal_dil or 0),
                                    "source": "ublox"}
                    except pynmea2.ParseError:
                        pass
        self.lat += 1e-6 + random.uniform(-1, 1) * 2e-6
        self.lon += 1e-6 + random.uniform(-1, 1) * 2e-6
        return {"lat": self.lat, "lon": self.lon, "alt": 10.0, "sats": 10, "hdop": 1.2, "source": "simulated"}