import base64
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES
import os
import logging

class SimpleCrypto:
    def __init__(self, key=None):
        self.key = key or os.urandom(32)  # 256-bit key
        self.iv = os.urandom(16)  # 128-bit IV
    
    def encrypt(self, data):
        if isinstance(data, dict):
            data = json.dumps(data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = self._pad(data.encode())
        return base64.b64encode(self.iv + cipher.encrypt(padded_data))
    
    def decrypt(self, encrypted_data):
        encrypted_data = base64.b64decode(encrypted_data)
        iv = encrypted_data[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = self._unpad(cipher.decrypt(encrypted_data[16:]))
        return decrypted.decode()
    
    def _pad(self, s):
        return s + (AES.block_size - len(s) % AES.block_size) * \
               chr(AES.block_size - len(s) % AES.block_size).encode()
    
    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

# Использование того же интерфейса для совместимости
class CryptoManager(SimpleCrypto):
    def get_key(self):
        return base64.b64encode(self.key).decode()