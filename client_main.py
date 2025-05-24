import sys
import os
from Client.gui import run_gui
import logging

# Добавляем путь к проекту в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='disk_usage_client.log'
)

if __name__ == "__main__":
    run_gui()