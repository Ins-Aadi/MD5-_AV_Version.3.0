import shutil
from datetime import datetime
import psutil

# ---------------- Configuration ---------------- #

CPU_THRESHOLD = 80.0
RAM_THRESHOLD = 80.0
DISK_THRESHOLD = 85.0


def get_system_status():
    """
    Returns complete system information as a dictionary.
    """

    cpu_usage = psutil.cpu_percent(interval=1)

    ram = psutil.virtual_memory()

    disk = shutil.disk_usage("/")

    net = psutil.net_io_counters()

    alerts = []

    if cpu_usage > CPU_THRESHOLD:
        alerts.append("High CPU usage detected.")

    if ram.percent > RAM_THRESHOLD:
        alerts.append("High RAM usage detected.")

    disk_percent = (disk.used / disk.total) * 100

    if disk_percent > DISK_THRESHOLD:
        alerts.append("Disk storage is almost full.")

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "cpu": {
            "usage": cpu_usage
        },

        "ram": {
            "usage": ram.percent,
            "used_mb": ram.used // (1024 ** 2),
            "total_mb": ram.total // (1024 ** 2),
            "available_mb": ram.available // (1024 ** 2)
        },

        "disk": {
            "usage": round(disk_percent, 1),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2)
        },

        "network": {
            "sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
            "received_mb": round(net.bytes_recv / (1024 ** 2), 2)
        },

        "alerts": alerts
    }


def get_alerts():
    """
    Returns only current alerts.
    """
    return get_system_status()["alerts"]


def is_system_healthy():
    """
    Returns True if no thresholds are exceeded.
    """
    return len(get_alerts()) == 0


def get_summary():
    """
    Returns a human-readable system summary.
    """

    status = get_system_status()

    return (
        f"CPU: {status['cpu']['usage']}% | "
        f"RAM: {status['ram']['usage']}% | "
        f"Disk: {status['disk']['usage']}% | "
        f"Network: ↑ {status['network']['sent_mb']} MB "
        f"↓ {status['network']['received_mb']} MB"
    )