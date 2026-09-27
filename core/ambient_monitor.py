import time
import psutil


class AmbientMonitor:
    def __init__(self):
        self.last_battery_alert = 0
        self.last_ram_alert = 0

    def check_vitals(self) -> str | None:
        """
        Silently polls hardware metrics.
        Returns a proactive voice alert string if a critical anomaly is found.
        """
        now = time.time()

        # 1. Critical Battery Warning (Unplugged and <= 20%, alerted at most once every 10 mins)
        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged and battery.percent <= 20:
            if (now - self.last_battery_alert) > 600:
                self.last_battery_alert = now
                return f"Power levels critical at {battery.percent} percent. Please connect the power adapter, sir."

        # 2. RAM Saturation Alert (RAM >= 93%, alerted at most once every 15 mins)
        ram = psutil.virtual_memory().percent
        if ram >= 93:
            if (now - self.last_ram_alert) > 900:
                self.last_ram_alert = now
                return f"Memory load is peaking at {ram} percent. Background processes may require optimization."

        return None