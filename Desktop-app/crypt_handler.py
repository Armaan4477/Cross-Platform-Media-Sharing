from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
import sys
from loges import logger
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QDialog, QLabel, QGridLayout, QPushButton, QApplication, QSpacerItem, QSizePolicy, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QScreen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

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
    #com.an.Datadash

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
    #com.an.Datadash

    derived_key = derive_key(key, salt)

    cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(padded_data) + unpadder.finalize()

    directory = os.path.dirname(filepath)
    original_name, extension = os.path.splitext(os.path.basename(filepath.replace('.crypt', '')))
    file_name = f"{original_name}{extension}"

    i = 1
    while os.path.exists(os.path.join(directory, file_name)):
        file_name = f"{original_name} ({i}){extension}"
        i += 1
        #com.an.Datadash

    output_file_path = os.path.join(directory, file_name)
    with open(output_file_path, 'wb') as f:
        f.write(decrypted_data)


class Decryptor(QWidget):
    def __init__(self, file_list):
        super().__init__()
        self.initUI()
        self.encrypted_files = file_list
        self.pass_attempts = 3
        self.setFixedSize(400, 200)
        self.set_background()
        self.center_window()

    def initUI(self):
        self.setWindowTitle('Decryptor')
        self.setGeometry(100, 100, 400, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(30, 20, 30, 20)
        
        self.password_label = QLabel('Decryption Password:', self)
        self.style_label(self.password_label)
        layout.addWidget(self.password_label)
        #com.an.Datadash

        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addItem(spacer)

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.style_input(self.password_input)
        layout.addWidget(self.password_input)
        
        self.submit_button = QPushButton('Submit', self)
        self.style_button(self.submit_button)
        layout.addWidget(self.submit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.submit_button.clicked.connect(self.decrypt_all_files)
        self.setLayout(layout)


    def decrypt_all_files(self, pass_attempts = 3):
        password = self.password_input.text()
        if not password:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Input Error")
                msg_box.setText("Please Enter a Password.")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                msg_box.setStyleSheet("""
                    QMessageBox {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 1,
                            stop: 0 #b0b0b0,
                            stop: 1 #505050
                        );
                        color: #FFFFFF;
                        font-size: 16px;
                    }
                    QLabel {
                    background-color: transparent;
                    }
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(47, 54, 66, 255),
                            stop: 1 rgba(75, 85, 98, 255)
                        );
                        color: white;
                        border-radius: 10px;
                        border: 1px solid rgba(0, 0, 0, 0.5);
                        padding: 4px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(60, 68, 80, 255),
                            stop: 1 rgba(90, 100, 118, 255)
                        );
                    }
                    QPushButton:pressed {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(35, 41, 51, 255),
                            stop: 1 rgba(65, 75, 88, 255)
                        );
                    }
                """)
                msg_box.exec()
            
                return

        failed = False

        for f in self.encrypted_files:
            logger.debug("Decrypting %s with password %s", f, password)
            try:
                decrypt_file(f, password)
                logger.debug("Decrypted: %s", f)
            except:
                if self.pass_attempts > 0:
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("Input Error")
                        msg_box.setText(f"Try again, Remaining attempts: {self.pass_attempts}")
                        msg_box.setIcon(QMessageBox.Icon.Critical)
                        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                        msg_box.setStyleSheet("""
                            QMessageBox {
                                background: qlineargradient(
                                    x1: 0, y1: 0, x2: 1, y2: 1,
                                    stop: 0 #b0b0b0,
                                    stop: 1 #505050
                                );
                                color: #FFFFFF;
                                font-size: 16px;
                            }
                            QLabel {
                            background-color: transparent; 
                            }
                            QPushButton {
                                background: qlineargradient(
                                    x1: 0, y1: 0, x2: 1, y2: 0,
                                    stop: 0 rgba(47, 54, 66, 255),
                                    stop: 1 rgba(75, 85, 98, 255)
                                );
                                color: white;
                                border-radius: 10px;
                                border: 1px solid rgba(0, 0, 0, 0.5);
                                padding: 4px;
                                font-size: 16px;
                            }
                            QPushButton:hover {
                                background: qlineargradient(
                                    x1: 0, y1: 0, x2: 1, y2: 0,
                                    stop: 0 rgba(60, 68, 80, 255),
                                    stop: 1 rgba(90, 100, 118, 255)
                                );
                            }
                            QPushButton:pressed {
                                background: qlineargradient(
                                    x1: 0, y1: 0, x2: 1, y2: 0,
                                    stop: 0 rgba(35, 41, 51, 255),
                                    stop: 1 rgba(65, 75, 88, 255)
                                );
                            }
                        """)
                        msg_box.exec()
                        self.pass_attempts -= 1
                        return
                else:
                    failed = True
            os.remove(f)

        if failed:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Input Error")
                msg_box.setText("Too many incorrect attempts, File has been deleted.")
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                msg_box.setStyleSheet("""
                    QMessageBox {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 1,
                            stop: 0 #b0b0b0,
                            stop: 1 #505050
                        );
                        color: #FFFFFF;
                        font-size: 16px;
                    }
                    QLabel {
                    background-color: transparent; 
                    }
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(47, 54, 66, 255),
                            stop: 1 rgba(75, 85, 98, 255)
                        );
                        color: white;
                        border-radius: 10px;
                        border: 1px solid rgba(0, 0, 0, 0.5);
                        padding: 4px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(60, 68, 80, 255),
                            stop: 1 rgba(90, 100, 118, 255)
                        );
                    }
                    QPushButton:pressed {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(35, 41, 51, 255),
                            stop: 1 rgba(65, 75, 88, 255)
                        );
                    }
                """)
                msg_box.exec()
        else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Success")
                msg_box.setText("Successfully decrypted files")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                msg_box.setStyleSheet("""
                    QMessageBox {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 1,
                            stop: 0 #b0b0b0,
                            stop: 1 #505050
                        );
                        color: #FFFFFF;
                        font-size: 16px;
                    }
                    QLabel {
                    background-color: transparent;
                    }
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(47, 54, 66, 255),
                            stop: 1 rgba(75, 85, 98, 255)
                        );
                        color: white;
                        border-radius: 10px;
                        border: 1px solid rgba(0, 0, 0, 0.5);
                        padding: 4px;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(60, 68, 80, 255),
                            stop: 1 rgba(90, 100, 118, 255)
                        );
                    }
                    QPushButton:pressed {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 rgba(35, 41, 51, 255),
                            stop: 1 rgba(65, 75, 88, 255)
                        );
                    }
                """)
                msg_box.exec()
        self.hide()

    def set_background(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,
                    stop: 1 #505050
                );
            }
        """)

    def style_button(self, button):
        button.setFixedSize(150, 40)
        button.setFont(QFont("Arial", 15))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),  
                    stop: 1 rgba(75, 85, 98, 255)   
                );
                color: white;
                border-radius: 18px;
                border: 1px solid rgba(0, 0, 0, 0.5);
                padding: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(60, 68, 80, 255),  
                    stop: 1 rgba(90, 100, 118, 255) 
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(35, 41, 51, 255), 
                    stop: 1 rgba(65, 75, 88, 255)  
                );
            }
        """)

        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)  
        glow_effect.setXOffset(0)   
        glow_effect.setYOffset(0) 
        glow_effect.setColor(QColor(255, 255, 255, 100)) 
        button.setGraphicsEffect(glow_effect)

    def style_label(self, label):
        label.setStyleSheet("""
            color: #FFFFFF;
            background-color: transparent;  
            font-size: 20px;
        """)

    def style_input(self, input_field):
        input_field.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background-color: transparent;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                caret-color: #00FF00; 
            }
            QLineEdit:focus {
                border: 2px solid #333333; 
                caret-color: #00FF00; 
                background-color: rgba(255, 255, 255, 0.1); 
            }
        """)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 400, 200
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        #com.an.Datadash


# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     dialog = PasswordDialog()
    
#     if dialog.exec() == QDialog.DialogCode.Accepted:
#         password = dialog.getPassword()
#         print(f'Password entered: {password}')

#     sys.exit(app.exec())
