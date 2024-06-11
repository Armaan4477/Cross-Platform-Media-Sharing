from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QLineEdit
)
import sys

def derive_key(key: str, salt: bytes) -> bytes:
    """Derive a key using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(key.encode())

def encrypt_file(filepath: str, key: str):
    salt = os.urandom(16)
    derived_key = derive_key(key, salt)

    with open(filepath, 'rb') as f:
        data = f.read()

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    with open(filepath + '.crypt', 'wb') as f:
        f.write(salt + iv + encrypted_data)

    return filepath + '.crypt'

def decrypt_file(filepath: str, key: str):
    with open(filepath, 'rb') as f:
        data = f.read()

    salt = data[:16]
    iv = data[16:32]
    encrypted_data = data[32:]

    derived_key = derive_key(key, salt)

    cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(padded_data) + unpadder.finalize()

    with open(filepath.replace('.crypt', ''), 'wb') as f:
        f.write(decrypted_data)


def PasswordDialog(self_instance):
    password, ok = QInputDialog.getText(self_instance, 'Password Dialog', 'Enter Password:', echo=QLineEdit.EchoMode.Password)
        
    if ok:
        if not password:
            QMessageBox.warning(self_instance, 'Input Error', 'Password cannot be empty.')
            return PasswordDialog(self_instance)
        else:
            return password


# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     dialog = PasswordDialog()
    
#     if dialog.exec() == QDialog.DialogCode.Accepted:
#         password = dialog.getPassword()
#         print(f'Password entered: {password}')

#     sys.exit(app.exec())

