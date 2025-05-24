import psutil
import time
import getpass
import platform
import logging

def get_system_info():
    """Получение корректной информации о системе и дисках"""
    disk_info = []
    
    # Получаем информацию о всех разделах
    for partition in psutil.disk_partitions(all=False):
        try:
            # Пропускаем специальные файловые системы
            if partition.fstype in ('squashfs', 'tmpfs', 'devtmpfs'):
                continue
                
            usage = psutil.disk_usage(partition.mountpoint)
            
            # Конвертируем байты в гигабайты
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            
            disk_info.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'total': total_gb,
                'used': used_gb,
                'free': free_gb,
                'percent': usage.percent,
                'fstype': partition.fstype
            })
        except Exception as e:
            logging.error(f"Error getting disk info for {partition.mountpoint}: {e}")
            continue
    
    # Получаем информацию о системе
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time
    
    return {
        'disks': disk_info,
        'username': getpass.getuser(),
        'hostname': platform.node(),
        'os': f"{platform.system()} {platform.release()}",
        'uptime': uptime,
        'cpu_count': psutil.cpu_count(),
        'total_memory': psutil.virtual_memory().total / (1024 ** 3),  # в ГБ
        'available_memory': psutil.virtual_memory().available / (1024 ** 3),  # в ГБ
        'timestamp': time.time()
    }