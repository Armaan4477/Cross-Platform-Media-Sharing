import json
import platform
import os
import logging
import socket

logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('FileSharing: ')

logger.setLevel(logging.DEBUG)

# Define the config file name and current version
config_file_name = ".config.json"
current_version = "5"  # Set the current version of the json config file
app_version = "3.0"  # Set the current version of the application

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
#com.an.Datadash

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
    #com.an.Datadash


if not os.path.exists(config_file):
    file_path = get_default_path()

    default_config = {
        "version": current_version,
        "app_version": app_version,
        "device_name": platform.node(),
        "save_to_directory": file_path,
        "max_filesize": 1000,
        "encryption": False,
        "android_encryption": False,
        "show_warning": True
    }

    write_config(default_config, config_file)
    logger.info("Created new configuration file.")

else:
    config_data = get_config(config_file)

    if "version" not in config_data or config_data["version"] != current_version:
        logger.warning("Configuration version mismatch or missing. Overwriting with default config.")
        file_path = get_default_path()
        
        default_config = {
            "version": current_version,
            "app_version": app_version,
            "device_name": platform.node(),
            "save_to_directory": file_path,
            "max_filesize": 1000,
            "encryption": False,
            "android_encryption": False,
            "show_warning": True
        }
        
        write_config(default_config, config_file)
    else:
        logger.info("Loaded configuration: %s", config_data)
        #com.an.Datadash

def get_broadcast():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        logger.info("Local IP determined: %s", local_ip)
    except Exception as e:
        logger.error("Error obtaining local IP: %s", e)
        local_ip = "Unable to get IP"
    finally:
        s.close()
    
    if local_ip == "Unable to get IP":
        return local_ip

    # Split the IP address into parts
    ip_parts = local_ip.split('.')
    # Replace the last part with '255' to create the broadcast address
    ip_parts[-1] = '255'
    # Join the parts back together to form the broadcast address
    broadcast_address = '.'.join(ip_parts)
    logger.info("Broadcast address determined: %s", broadcast_address)
    return broadcast_address
#com.an.Datadash

BROADCAST_ADDRESS = get_broadcast()
BROADCAST_PORT = 12345
LISTEN_PORT = 12346

logger.info("Broadcast address: %s, Broadcast port: %d, Listen port: %d", BROADCAST_ADDRESS, BROADCAST_PORT, LISTEN_PORT)
#com.an.Datadash
