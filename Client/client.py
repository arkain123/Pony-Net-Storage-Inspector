import socket
import json
import logging
from cryptography.fernet import Fernet, InvalidToken

import psutil
import platform
import getpass
from datetime import datetime

class DiskUsageClient:
    def __init__(self, host, port=65432):
        self.host = host
        self.port = port
        self.timeout = 5
        self.buffer_size = 4096
        self.logger = logging.getLogger(__name__)

    def _receive_all(self, sock):
        """Получение всех доступных данных"""
        data = b''
        sock.settimeout(self.timeout)
        
        try:
            while True:
                chunk = sock.recv(self.buffer_size)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
            
        return data

    def connect(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)  # Общий таймаут 10 секунд
            
            # Подключение
            sock.connect((self.host, self.port))
            
            # 1. Получаем ключ до разделителя
            key_data = b''
            while True:
                chunk = sock.recv(1)
                if chunk == b'\x00':  # Наш разделитель
                    break
                if not chunk:
                    raise ValueError("Key transmission interrupted")
                key_data += chunk
            
            # 2. Отправляем подтверждение
            sock.sendall(b'KEY_RECEIVED\n')  # Явный перевод строки
            
            # 3. Отправляем запрос
            sock.sendall(b'get_disk_info\n')
            
            # 4. Получаем данные
            encrypted_data = self._receive_all(sock)
            if not encrypted_data:
                raise ValueError("No data received")
            
            # Дешифровка
            cipher = Fernet(key_data)
            return json.loads(cipher.decrypt(encrypted_data).decode())
            
        except Exception as e:
            raise ValueError(f"Connection error: {str(e)}")
        finally:
            if sock:
                sock.close()

    def _receive_all(self, sock):
        """Получаем все данные до закрытия соединения"""
        data = b''
        sock.settimeout(5.0)
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        return data

    def _receive_until_newline(self, sock):
        """Чтение данных до символа новой строки"""
        data = b''
        while True:
            chunk = sock.recv(1)
            if not chunk or chunk == b'\n':
                break
            data += chunk
        return data