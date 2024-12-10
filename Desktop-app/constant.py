import json
import platform
import os
import logging
import socket

# Define the config file name and current version
config_file_name = ".config.json"
current_version = "3.4.4"  # Set the current version of the json config file (app version)


def get_logger_file_path():
    if platform.system() == 'Windows':
        logger_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Temp' ,  'DataDash')
    elif platform.system() == 'Linux':
        logger_dir = os.path.join(os.path.expanduser('~'), '.cache', 'DataDash')
    elif platform.system() == 'Darwin':  # macOS
        logger_dir = os.path.join(os.path.expanduser('~/Library/Caches'), 'DataDash')
    else:
        return None
    
    # Create the directory if it doesn't exist
    os.makedirs(logger_dir, exist_ok=True)
    return logger_dir


# Create logger directory and set up the log file path
log_dir = get_logger_file_path()
if (log_dir is None):
    raise RuntimeError("Unsupported OS!")
    
log_file_path = os.path.join(log_dir, 'datadashlog.txt')

# Configure the logger
logger = logging.getLogger('FileSharing: ')
logger.setLevel(logging.DEBUG)

# Create a formatter with date and time
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

# Create a FileHandler to write logs to 'datadashlog.txt'
file_handler = logging.FileHandler(log_file_path, mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Create a StreamHandler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger = logging.getLogger('FileSharing: ')

logger.setLevel(logging.DEBUG)

logger.info("App version: %s", current_version)

def get_config_file_path():
    if platform.system() == 'Windows':
        cache_dir = os.path.join(os.getenv('APPDATA'), 'DataDash')
    elif platform.system() == 'Linux':
        cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'DataDash')
    elif platform.system() == 'Darwin':  # macOS
        cache_dir = os.path.join(os.path.expanduser('~/Library/Application Support'), 'DataDash')
    else:
        logger.error("Unsupported OS!")
        return None

    os.makedirs(cache_dir, exist_ok=True)
    logger.info("Config directory created/ensured: %s", cache_dir)
    return os.path.join(cache_dir, config_file_name)

config_file = get_config_file_path()
if config_file is None:
    exit(1)

def get_default_path():
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
        logger.error("Unsupported OS!")
        file_path = None
    logger.info("Default path determined: %s", file_path)
    return file_path

def write_config(data, filename=config_file):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    logger.info("Configuration written to %s", filename)

def get_config(filename=config_file):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        logger.info("Loaded configuration from %s", filename)
        return data
    except FileNotFoundError:
        logger.warning("Configuration file %s not found. Returning empty config.", filename)
        return {}

if not os.path.exists(config_file):
    file_path = get_default_path()

    default_config = {
        "version": current_version,
        "device_name": platform.node(),
        "save_to_directory": file_path,
        "max_filesize": 1000,
        "encryption": False,
        "android_encryption": False,
        "swift_encryption": False,
        "show_warning": True,
        "check_update": True,
        "update_channel": "stable"
    }

    write_config(default_config, config_file)
    logger.info("Created new configuration file.")

else:
    config_data = get_config(config_file)

    if "version" not in config_data or config_data["version"] != current_version:
        logger.warning("Configuration version mismatch or missing. Overwriting with default config.")

        # Carry over existing values
        device_name = config_data.get("device_name", platform.node())
        save_to_directory = config_data.get("save_to_directory", get_default_path())
        encryption = config_data.get("encryption", False)
        channel = config_data.get("update_channel", "stable")
        warnings = config_data.get("show_warning", True)

        default_config = {
            "version": current_version,
            "device_name": device_name,
            "save_to_directory": save_to_directory,
            "max_filesize": 1000,
            "encryption": encryption,
            "android_encryption": False,
            "swift_encryption": False,
            "show_warning": warnings,
            "check_update": True,
            "update_channel": channel
        }

        write_config(default_config, config_file)
    else:
        logger.info("Loaded configuration: %s", config_data)

BROADCAST_PORT = 49185
LISTEN_PORT = 49186
RECEIVER_JSON = 54314

logger.info("Broadcast port: %d, Listen port: %d", BROADCAST_PORT, LISTEN_PORT)
#com.an.Datadash
