import json
import platform
import os
from PyQt6.QtCore import QThread, pyqtSignal
from loges import logger

class ConfigManager(QThread):
    config_updated = pyqtSignal(dict)
    config_ready = pyqtSignal()
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.config_file_name = ".config.json"
        self.current_version = "4.4.3"
        self.config_file = self.get_config_file_path()

    def get_config_file_path(self):
        if platform.system() == 'Windows':
            cache_dir = os.path.join(os.getenv('APPDATA'), 'DataDash')
        elif platform.system() == 'Linux':
            cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'DataDash')
        elif platform.system() == 'Darwin':
            cache_dir = os.path.join(os.path.expanduser('~/Library/Application Support'), 'DataDash')
        else:
            self.log_message.emit("Unsupported OS!")
            return None

        os.makedirs(cache_dir, exist_ok=True)
        self.log_message.emit(f"Config directory created/ensured: {cache_dir}")
        return os.path.join(cache_dir, self.config_file_name)

    def get_default_path(self):
        if platform.system() == 'Windows':
            file_path = "C:\\Received"
        elif platform.system() == 'Linux':
            home_dir = os.path.expanduser('~')
            os.makedirs(os.path.join(home_dir, "received"), exist_ok=True)
            file_path = os.path.join(home_dir, "received")
        elif platform.system() == 'Darwin':
            home_dir = os.path.expanduser('~')
            documents_dir = os.path.join(home_dir, "Documents")
            os.makedirs(os.path.join(documents_dir, "received"), exist_ok=True)
            file_path = os.path.join(documents_dir, "received")
        else:
            self.log_message.emit("Unsupported OS!")
            file_path = None
        self.log_message.emit(f"Default path determined: {file_path}")
        return file_path

    def write_config(self, data):
        with open(self.config_file, 'w') as file:
            json.dump(data, file, indent=4)
        self.log_message.emit(f"Configuration written to {self.config_file}")
        self.config_updated.emit(data)

    def get_config(self):
        try:
            with open(self.config_file, 'r') as file:
                data = json.load(file)
            self.log_message.emit(f"Loaded configuration from {self.config_file}")
            return data
        except FileNotFoundError:
            self.log_message.emit(f"Configuration file {self.config_file} not found. Returning empty config.")
            return {}

    def run(self):
        if not os.path.exists(self.config_file):
            file_path = self.get_default_path()
            default_config = {
                "version": self.current_version,
                "device_name": platform.node(),
                "save_to_directory": file_path,
                "max_filesize": 1000,
                "encryption": False,
                "swift_encryption": False,
                "show_warning": True,
                "check_update": True,
                "update_channel": "stable"
            }
            self.write_config(default_config)
            self.log_message.emit("Created new configuration file.")
        else:
            config_data = self.get_config()
            if "version" not in config_data or config_data["version"] != self.current_version:
                self.log_message.emit("Configuration version mismatch or missing. Overwriting with default config.")
                device_name = config_data.get("device_name", platform.node())
                save_to_directory = config_data.get("save_to_directory", self.get_default_path())
                encryption = config_data.get("encryption", False)
                channel = config_data.get("update_channel", "stable")
                warnings = config_data.get("show_warning", True)

                default_config = {
                    "version": self.current_version,
                    "device_name": device_name,
                    "save_to_directory": save_to_directory,
                    "max_filesize": 1000,
                    "encryption": encryption,
                    "swift_encryption": False,
                    "show_warning": warnings,
                    "check_update": True,
                    "update_channel": channel
                }
                self.write_config(default_config)
            else:
                self.log_message.emit(f"Loaded configuration: {config_data}")
                self.config_updated.emit(config_data)
        self.config_ready.emit()
