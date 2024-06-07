import json
import platform
from sys import exit
import os

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
        "max_filesize": 1,
        "encryption": False
    }

    write_config(default_config, config_file)

BROADCAST_ADDRESS = '255.255.255.255'
BROADCAST_PORT = 12345
LISTEN_PORT = 12346
