import sys
from PyQt6.QtWidgets import QDialog, QLabel, QGridLayout, QPushButton, QApplication, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QScreen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

class CreditsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Credits")
        self.setFixedSize(520, 425)
        self.set_background()
        self.center_window()

        layout = QGridLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title_coder = QLabel("Core Team")
        title_coder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_coder.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_coder, 0, 0, 1, 3)

        layout.addWidget(QLabel("Armaan Nakhuda", font=QFont("Arial", 18)), 2, 0)
        armaan_github = self.create_link_button("GitHub", "https://github.com/Armaan4477")
        layout.addWidget(armaan_github, 2, 1)

        armaan_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/armaan-nakhuda-756492235/")
        layout.addWidget(armaan_linkedin, 2, 2)

        layout.addWidget(QLabel("Samay Pandey", font=QFont("Arial", 18)), 3, 0)
        samay_github = self.create_link_button("GitHub", "https://github.com/ChampionSamay1644")
        layout.addWidget(samay_github, 3, 1)

        samay_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/samaypandey1644")
        layout.addWidget(samay_linkedin, 3, 2)
        #com.an.Datadash

        layout.addWidget(QLabel("Yash Patil", font=QFont("Arial", 18)), 4, 0) 
        yash_github = self.create_link_button("GitHub", "https://github.com/FrosT2k5")
        layout.addWidget(yash_github, 4, 1)

        yash_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/yash-patil-385171257")
        layout.addWidget(yash_linkedin, 4, 2)

        layout.addWidget(QLabel("Aarya Walve", font=QFont("Arial", 18)), 5, 0)
        aarya_github = self.create_link_button("GitHub", "https://github.com/aaryaa28")
        layout.addWidget(aarya_github, 5, 1)

        aarya_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/aarya-walve-10259325b/")
        layout.addWidget(aarya_linkedin, 5, 2)

        layout.addWidget(QLabel("Special Thanks:", font=QFont("Arial", 18)), 6, 0)
        layout.addWidget(QLabel("Nishal P, Urmi J, Adwait P", font=QFont("Arial", 18)), 6, 1)

        #com.an.Datadash

        close_button = QPushButton("Close")
        self.style_button(close_button)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, 13, 0, 1, 3)

        self.setLayout(layout)

    def set_background(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #b0b0b0,  /* Start color */
                    stop: 1 #505050   /* End color */
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
                    stop: 0 rgba(47, 54, 66, 255),   /* Dark Color */
                    stop: 1 rgba(75, 85, 98, 255)    /* Light Color */
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
                    stop: 0 rgba(60, 68, 80, 255),   /* Lightened Dark Color */
                    stop: 1 rgba(90, 100, 118, 255)  /* Lightened Light Color */
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(35, 41, 51, 255),   /* Darker on press */
                    stop: 1 rgba(65, 75, 88, 255)    /* Darker on press */
                );
            }
        """)

        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15) 
        glow_effect.setXOffset(0)  
        glow_effect.setYOffset(0)
        glow_effect.setColor(QColor(255, 255, 255, 100)) 
        button.setGraphicsEffect(glow_effect)

    def create_link_button(self, text, url):
        button = QPushButton(text)
        self.style_button(button)
        button.setStyleSheet(button.styleSheet() + "QPushButton { text-align: center; }")
        button.clicked.connect(lambda: self.open_link(url)) 
        return button

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        window_width, window_height = 520, 425
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CreditsDialog()
    dialog.exec()
