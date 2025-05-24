import socket
import threading
import json
import psutil
import time
import logging
import platform
import getpass
from cryptography.fernet import Fernet

class DiskUsageServer:
    def __init__(self, host='0.0.0.0', port=65432):
        self.host = host
        self.port = port
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        self.running = False
        self.server_socket = None
        self.setup_logging()

    def loginfo(self, message):
        logging.info(message)
        print(message)

    def logerr(self, message, exc_info=False):
        logging.error(message, exc_info=exc_info)
        print(message)

    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='disk_usage_server.log'
        )

    def get_system_info(self):
        """Получение информации о системе"""
        disks = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'total': round(usage.total / (1024**3), 2),  # в ГБ
                    'used': round(usage.used / (1024**3), 2),
                    'free': round(usage.free / (1024**3), 2),
                    'percent': usage.percent,
                    'fstype': partition.fstype
                })
            except Exception as e:
                self.logerr(f"Disk {partition.mountpoint} error: {e}")

        return {
            'disks': disks,
            'username': getpass.getuser(),
            'hostname': platform.node(),
            'os': f"{platform.system()} {platform.release()}",
            'uptime': round((time.time() - psutil.boot_time()) / 3600, 1),  # в часах
            'cpu_count': psutil.cpu_count(),
            'memory_total': round(psutil.virtual_memory().total / (1024**3), 1),  # в ГБ
            'timestamp': time.time()
        }

    def handle_client(self, client_socket, address):
        try:
            self.loginfo(f"Connection from {address}")

            # 1. Отправляем ключ клиенту
            client_socket.sendall(self.key + b'\x00')
            
            # 2. Ждем подтверждения с таймаутом
            client_socket.settimeout(5.0)
            ack = client_socket.recv(1024)
            
            if not ack:
                raise ValueError("Client closed connection without acknowledgment")
            if ack.strip() != b'KEY_RECEIVED':
                raise ValueError(f"Invalid key acknowledgment: {ack!r}")

            # 3. Получаем запрос
            request = client_socket.recv(1024)
            if not request:
                raise ValueError("Client closed connection without request")
            if request.strip() != b'get_disk_info':
                raise ValueError(f"Invalid request: {request!r}")

            # 4. Отправляем данные
            system_info = self.get_system_info()
            encrypted = self.cipher.encrypt(json.dumps(system_info).encode())
            client_socket.sendall(encrypted)

        except socket.timeout:
            self.logerr(f"Timeout with {address}")
        except Exception as e:
            self.logerr(f"Error with {address}: {str(e)}", exc_info=True)
        finally:
            client_socket.close()

    def start(self):
        """Запуск сервера"""
        self.running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.loginfo(f"Server started on {self.host}:{self.port}")

            while self.running:
                client_socket, address = self.server_socket.accept()
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()

        except Exception as e:
            self.logerr(f"Server error: {e}", exc_info=True)
            self.stop()

    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.loginfo("Server stopped gracefully")


def main():
    """Точка входа для запуска сервера"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='disk_usage_server.log'
    )
    
    server = DiskUsageServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        server.stop()

if __name__ == "__main__":
    main()