import json
import platform
from sys import exit
import os
import logging
import socket

# Define the logger configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create the logger instance
logger = logging.getLogger('FileSharing: ')

# Set the logger level to debug
logger.setLevel(logging.DEBUG)

config_file = ".config.json"

def get_default_path():
    if platform.system() == 'Windows':
        file_path = "c:\\Received"
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
        print("Unsupported OS!")
        file_path = None
    return file_path

def write_config(data, filename=config_file):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def get_config(filename=config_file):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        return {}

if not os.path.exists(config_file):
    file_path = get_default_path()

    default_config = {
        "device_name": platform.node(),
        "save_to_directory": file_path,
        "max_filesize": 1000,
        "encryption": False,
        "show_warning": True
    }

    write_config(default_config, config_file)


def get_broadcast():
    try:
        # Create a socket to connect to a remote server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Attempt to connect to an external server (this will not send data)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception as e:
        # Fallback in case of error
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
    return broadcast_address

    
BROADCAST_ADDRESS = get_broadcast()
BROADCAST_PORT = 12345
LISTEN_PORT = 12346
