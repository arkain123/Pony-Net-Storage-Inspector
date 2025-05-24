import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import json
import logging
import ipaddress
import socket
import platform
from datetime import datetime
from .client import DiskUsageClient
from .local_info import LocalSystemInfo

class ToolTip:
    """Класс для всплывающих подсказок"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        """Показать подсказку"""
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            self.tip_window,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=('Arial', 10)
        )
        label.pack()

    def hide_tip(self, event=None):
        """Скрыть подсказку"""
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class DiskUsageApp:
    def __init__(self, root):
        self.root = root
        self.setup_variables()
        self.setup_ui()
        
    def setup_variables(self):
        """Инициализация переменных"""
        self.known_hosts_file = "known_hosts.json"
        self.known_hosts = self.load_known_hosts()
        self.active_hosts = []
        self.scanning = False
        self.results = {}
        self.local_hostnames = {platform.node(), 'localhost', '127.0.0.1'}
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.root.title("[PNSI] Pony Net Storage Inspector")
        self.root.geometry("1200x800")
        
        # Стили
        self.style = ttk.Style()
        self.style.configure('Local.TButton', foreground='blue', font=('Arial', 10, 'bold'))
        
        # Фрейм управления
        self.control_frame = ttk.Frame(self.root, padding="10")
        self.control_frame.pack(fill=tk.X)
        
        # Кнопки
        ttk.Button(
            self.control_frame,
            text="Сканировать сеть",
            command=self.start_network_scan
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            self.control_frame,
            text="Обновить данные",
            command=self.refresh_data
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            self.control_frame,
            text="Моя система",
            command=self.scan_local_system,
            style='Local.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            self.control_frame,
            text="Сохранить отчет",
            command=self.save_report
        ).pack(side=tk.LEFT, padx=5)
        
        # Поле диапазона IP
        ip_frame = ttk.Frame(self.control_frame)
        ip_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(ip_frame, text="Диапазон IP:").pack(side=tk.LEFT)
        
        self.ip_range_var = tk.StringVar(value="192.168.100.0/24")
        self.ip_range_entry = ttk.Entry(ip_frame, textvariable=self.ip_range_var, width=18)
        self.ip_range_entry.pack(side=tk.LEFT, padx=2)
        ToolTip(self.ip_range_entry, "Формат: XXX.XXX.XXX.XXX/XX или XXX.XXX.XXX.XXX-XXX")
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            self.control_frame,
            orient=tk.HORIZONTAL,
            mode='determinate'
        )
        self.progress.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Статус
        self.status_label = ttk.Label(self.control_frame, text="Готов")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Основное содержимое
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Список хостов
        self.host_frame = ttk.Frame(self.main_frame, width=300)
        self.host_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.host_list = tk.Listbox(
            self.host_frame,
            selectmode=tk.MULTIPLE,
            font=('Arial', 10)
        )
        self.host_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.host_frame, orient=tk.VERTICAL)
        scrollbar.config(command=self.host_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.host_list.config(yscrollcommand=scrollbar.set)
        
        # Информационная панель
        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Таблица данных
        self.tree = ttk.Treeview(
            self.info_frame,
            columns=('host', 'username', 'disk', 'total', 'used', 'free', 'percent', 'uptime'),
            show='headings'
        )
        
        # Настройка колонок
        columns = [
            ('host', 'Хост', 120),
            ('username', 'Пользователь', 100),
            ('disk', 'Диск', 100),
            ('total', 'Всего (ГБ)', 80),
            ('used', 'Использовано (ГБ)', 80),
            ('free', 'Свободно (ГБ)', 80),
            ('percent', 'Использовано (%)', 80),
            ('uptime', 'Время работы (ч)', 80)
        ]
        
        for col_id, col_text, col_width in columns:
            self.tree.heading(col_id, text=col_text)
            self.tree.column(col_id, width=col_width)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Теги для стилизации
        self.tree.tag_configure('local', background='#f0f8ff')
        
        # Журнал событий
        self.log_frame = ttk.Frame(self.root)
        self.log_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        
        ttk.Label(self.log_frame, text="Журнал событий:").pack(anchor=tk.W)
        
        self.log_area = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=8,
            font=('Arial', 9)
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Обновляем список хостов
        self.update_host_list()
        
        # Горячие клавиши
        self.root.bind('<F5>', lambda e: self.scan_local_system())

    def load_known_hosts(self):
        """Загрузка списка известных хостов"""
        if os.path.exists(self.known_hosts_file):
            try:
                with open(self.known_hosts_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.log_message(f"Ошибка загрузки хостов: {str(e)}")
                return []
        return []

    def save_known_hosts(self):
        """Сохранение списка хостов"""
        try:
            with open(self.known_hosts_file, 'w') as f:
                json.dump(self.known_hosts, f, indent=2)
        except Exception as e:
            self.log_message(f"Ошибка сохранения хостов: {str(e)}")

    def update_host_list(self):
        """Обновление списка хостов"""
        self.host_list.delete(0, tk.END)
        for host in self.known_hosts:
            is_local = host in self.local_hostnames
            status = "✓" if host in self.active_hosts else "✗"
            display = f"{status} {host} {'(этот компьютер)' if is_local else ''}"
            self.host_list.insert(tk.END, display)

    def scan_local_system(self):
        """Сканирование локальной системы"""
        try:
            local_info = LocalSystemInfo.get_full_info()
            hostname = local_info['hostname']
            
            if hostname not in self.known_hosts:
                self.known_hosts.append(hostname)
                self.save_known_hosts()
            
            if hostname not in self.active_hosts:
                self.active_hosts.append(hostname)
            
            self._display_system_info(hostname, local_info)
            self.update_host_list()
            self.log_message("✅ Локальная система просканирована")
            
        except Exception as e:
            self.log_message(f"❌ Ошибка самодиагностики: {str(e)}")
            logging.exception("Ошибка при сканировании локальной системы")

    def _display_system_info(self, host, info):
        """Отображение информации о системе"""
        # Очищаем предыдущие записи
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0].startswith(host):
                self.tree.delete(item)
        
        # Добавляем новые данные
        for disk in info.get('disks', []):
            self.tree.insert('', 'end', 
                values=(
                    f"{host} (локальный)",
                    info.get('username', 'N/A'),
                    disk.get('mountpoint', 'N/A'),
                    f"{disk.get('total', 0):.2f}",
                    f"{disk.get('used', 0):.2f}",
                    f"{disk.get('free', 0):.2f}",
                    f"{disk.get('percent', 0):.1f}",
                    f"{info.get('uptime', 0)/3600:.1f}"
                ),
                tags=('local',)
            )

    def start_network_scan(self):
        """Запуск сканирования сети"""
        if self.scanning:
            return
            
        ip_range = self.ip_range_var.get().strip()
        if not self.validate_ip_range(ip_range):
            messagebox.showerror("Ошибка", "Укажите корректный диапазон IP")
            return
            
        self.scanning = True
        self.active_hosts = []
        self.progress['value'] = 0
        self.status_label['text'] = "Сканирование..."
        self.log_message(f"🔍 Начато сканирование: {ip_range}")
        
        threading.Thread(
            target=self.perform_network_scan,
            args=(ip_range,),
            daemon=True
        ).start()

    def validate_ip_range(self, ip_range):
        """Проверка валидности диапазона IP"""
        try:
            if '/' in ip_range:
                ipaddress.ip_network(ip_range, strict=False)
                return True
            elif '-' in ip_range:
                start, end = ip_range.split('-')
                ipaddress.ip_address(start.strip())
                ipaddress.ip_address(end.strip())
                return True
            return False
        except ValueError:
            return False

    def perform_network_scan(self, ip_range):
        """Выполнение сканирования сети"""
        try:
            # Определяем список IP для сканирования
            if '/' in ip_range:
                network = ipaddress.ip_network(ip_range, strict=False)
                ips_to_scan = [str(host) for host in network.hosts()]
            else:
                start, end = ip_range.split('-')
                start_ip = ipaddress.ip_address(start.strip())
                end_ip = ipaddress.ip_address(end.strip())
                ips_to_scan = [str(ipaddress.ip_address(ip)) 
                              for ip in range(int(start_ip), int(end_ip)+1)]
            
            total_ips = len(ips_to_scan)
            
            for i, ip in enumerate(ips_to_scan, 1):
                if not self.scanning:
                    break
                    
                progress = (i / total_ips) * 100
                self.root.after(0, lambda: self.progress.config(value=progress))
                self.root.after(0, lambda: self.status_label.config(text=f"Сканирование {ip}"))
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.2)
                        if s.connect_ex((ip, 65432)) == 0:
                            if ip not in self.known_hosts:
                                self.known_hosts.append(ip)
                            if ip not in self.active_hosts:
                                self.active_hosts.append(ip)
                            self.root.after(0, self.log_message, f"Найден сервер: {ip}")
                except:
                    continue
            
            self.save_known_hosts()
            self.root.after(0, self.update_host_list)
            self.root.after(0, lambda: self.log_message("✅ Сканирование завершено"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка сканирования: {str(e)}"))
            logging.exception("Ошибка при сканировании сети")
        finally:
            self.scanning = False
            self.root.after(0, lambda: self.status_label.config(text="Готово"))
            self.root.after(0, lambda: self.progress.config(value=0))

    def refresh_data(self):
        """Обновление данных с выбранных хостов"""
        selected_indices = self.host_list.curselection()
        if not selected_indices:
            messagebox.showwarning("Предупреждение", "Выберите хосты для обновления")
            return
        
        # Очищаем старые данные
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        total_hosts = len(selected_indices)
        success_count = 0
        
        for i, idx in enumerate(selected_indices, 1):
            host = self.known_hosts[idx]
            self.status_label['text'] = f"Запрос к {host}..."
            self.progress['value'] = (i / total_hosts) * 100
            self.root.update_idletasks()
            
            # Проверяем, не локальный ли это хост
            if host in self.local_hostnames:
                try:
                    self.scan_local_system()
                    success_count += 1
                except Exception as e:
                    self.log_message(f"❌ Ошибка локального сканирования: {str(e)}")
                continue
                
            # Обработка удаленных хостов
            try:
                client = DiskUsageClient(host)
                system_info = client.connect()
                
                if system_info:
                    for disk in system_info.get('disks', []):
                        self.tree.insert('', 'end', values=(
                            host,
                            system_info.get('username', 'N/A'),
                            disk.get('mountpoint', 'N/A'),
                            f"{disk.get('total', 0):.2f}",
                            f"{disk.get('used', 0):.2f}",
                            f"{disk.get('free', 0):.2f}",
                            f"{disk.get('percent', 0):.1f}",
                            f"{system_info.get('uptime', 0)/3600:.1f}"
                        ))
                    success_count += 1
                    self.log_message(f"✅ Данные с {host} получены")
                else:
                    self.log_message(f"⚠️ Нет данных от {host}")
                    
            except Exception as e:
                self.log_message(f"❌ Ошибка запроса к {host}: {str(e)}")
        
        self.status_label['text'] = "Готово"
        self.progress['value'] = 0
        messagebox.showinfo(
            "Обновление завершено",
            f"Успешно: {success_count}/{total_hosts}\nНе удалось: {total_hosts-success_count}"
        )

    def save_report(self):
        """Сохранение отчета"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"disk_report_{timestamp}.json"
            
            report_data = []
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                report_data.append({
                    'host': values[0],
                    'username': values[1],
                    'disk': values[2],
                    'total_gb': values[3],
                    'used_gb': values[4],
                    'free_gb': values[5],
                    'usage_percent': values[6],
                    'uptime_hours': values[7],
                    'is_local': '(локальный)' in values[0]
                })
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            self.log_message(f"📄 Отчет сохранен в {filename}")
            messagebox.showinfo("Успех", f"Отчет сохранен в:\n{filename}")
            
        except Exception as e:
            self.log_message(f"❌ Ошибка сохранения: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{str(e)}")

    def log_message(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
        logging.info(message)

def run_gui():
    """Запуск графического интерфейса"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='disk_usage_client.log'
    )
    
    root = tk.Tk()
    app = DiskUsageApp(root)
    root.mainloop()