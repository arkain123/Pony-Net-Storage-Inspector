import socket
import ipaddress
import logging

class NetworkScanner:
    @staticmethod
    def scan_network(network_range='192.168.100.0/24', port=65432, timeout=1):
        """Сканирование сети на наличие серверов"""
        active_hosts = []
        
        try:
            network = ipaddress.ip_network(network_range)
            logging.info(f"Scanning network: {network_range}")
            
            for ip in network.hosts():
                ip_str = str(ip)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(timeout)
                        result = sock.connect_ex((ip_str, port))
                        if result == 0:
                            active_hosts.append(ip_str)
                            logging.info(f"Found active server at {ip_str}")
                except Exception as e:
                    logging.debug(f"Error scanning {ip_str}: {e}")
                    continue
        
        except ValueError as e:
            logging.error(f"Invalid network range {network_range}: {e}")
        
        return active_hosts