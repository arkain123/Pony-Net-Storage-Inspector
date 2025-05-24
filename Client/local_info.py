import psutil
import platform
import getpass
from datetime import datetime

class LocalSystemInfo:
    @staticmethod
    def get_disk_info():
        """Получение информации о дисках"""
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'total': round(usage.total / (1024**3), 2),  # в ГБ
                    'used': round(usage.used / (1024**3), 2),
                    'free': round(usage.free / (1024**3), 2),
                    'percent': usage.percent,
                    'fstype': part.fstype
                })
            except Exception as e:
                continue
        return disks

    @classmethod
    def get_full_info(cls):
        """Полная информация о системе"""
        return {
            'disks': cls.get_disk_info(),
            'username': getpass.getuser(),
            'hostname': platform.node(),
            'os': f"{platform.system()} {platform.release()}",
            'uptime': round((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()),
            'cpu_count': psutil.cpu_count(),
            'memory_total': round(psutil.virtual_memory().total / (1024**3), 1),
            'is_local': True
        }