import psutil
import time
import getpass
import platform
import json

def get_system_info():
    disk_info = []
    for partition in psutil.disk_partitions(all=False):
        if not partition.mountpoint:
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent,
                'fstype': partition.fstype
            })
        except Exception as e:
            logging.error(f"Error getting disk info for {partition.mountpoint}: {e}")
            continue
    
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time
    
    return {
        'disks': disk_info,
        'username': getpass.getuser(),
        'hostname': platform.node(),
        'os': f"{platform.system()} {platform.release()}",
        'uptime': uptime,
        'cpu_count': psutil.cpu_count(),
        'total_memory': psutil.virtual_memory().total,
        'available_memory': psutil.virtual_memory().available,
        'timestamp': time.time()
    }