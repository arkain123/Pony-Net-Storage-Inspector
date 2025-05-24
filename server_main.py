from Server.server import DiskUsageServer

def run_server():
    """Функция для запуска сервера"""
    server = DiskUsageServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"Server error: {e}")
        server.stop()

if __name__ == "__main__":
    run_server()