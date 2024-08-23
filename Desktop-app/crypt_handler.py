from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QMessageBox
)
import sys
from constant import logger

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


class Decryptor(QWidget):
    def __init__(self, file_list):
        super().__init__()
        self.initUI()
        self.encrypted_files = file_list
        self.pass_attempts = 3

    def initUI(self):
        self.setWindowTitle('Decryptor')
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()
        self.password_label = QLabel('Decryption Password:', self)
        layout.addWidget(self.password_label)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.submit_button = QPushButton('Submit', self)

        layout.addWidget(self.password_input)
        layout.addWidget(self.submit_button)
        self.submit_button.clicked.connect(self.decrypt_all_files)
        self.setLayout(layout)

    def decrypt_all_files(self, pass_attempts = 3):
        password = self.password_input.text()
        if not password:
            QMessageBox.critical(self_instance, 'Input Error', 'Password cannot be empty.') # type: ignore
            return

        failed = False

        for f in self.encrypted_files:
            logger.debug("Decrypting %s with password %s", f, password)
            try:
                decrypt_file(f, password)
                logger.debug("Decrypted: %s", f)
            except:
                if self.pass_attempts > 0:
                    QMessageBox.critical(self, "Incorrect Password", f"Try again, Remaining attempts: {self.pass_attempts}.")
                    self.pass_attempts -= 1
                    return
                else:
                    failed = True
            os.remove(f)

        if failed:
            QMessageBox.critical(self, "Too many incorrect attempts", "File has been deleted.")
        else:
            QMessageBox.information(self, "Success", "Successfully decrypted files")
        self.hide()
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     dialog = PasswordDialog()
    
#     if dialog.exec() == QDialog.DialogCode.Accepted:
#         password = dialog.getPassword()
#         print(f'Password entered: {password}')

#     sys.exit(app.exec())

