import sys
from PyQt6.QtWidgets import QDialog, QLabel, QGridLayout, QPushButton, QApplication, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

class CreditsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Credits")
        self.setFixedSize(600, 625)  # Increased window size to provide more space
        self.set_background()  # Set the background style

        # Create layout for the dialog in grid form
        layout = QGridLayout()
        layout.setSpacing(10)  # Set spacing between rows
        layout.setContentsMargins(20, 20, 20, 20)  # Set margins for the layout

        # Title 1: Coder/Debugger
        title_coder = QLabel("Coder/Debugger")
        title_coder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_coder.setFont(QFont("Arial", 16, QFont.Weight.Bold))  # Use consistent font
        layout.addWidget(title_coder, 0, 0, 1, 3)  # Span across 3 columns

        # Table Headers for Coder/Debugger
        layout.addWidget(QLabel("<b>Name</b>"), 1, 0)
        layout.addWidget(QLabel("<b>GitHub</b>"), 1, 1)
        layout.addWidget(QLabel("<b>LinkedIn</b>"), 1, 2)

        # Coder/Debugger - Alphabetical Order (Armaan, Nishal, Samay, Urmi, Yash, Adwait)
        # Armaan's row
        layout.addWidget(QLabel("Armaan Nakhuda", font=QFont("Arial", 18)), 5, 0)  # Increased font size
        armaan_github = self.create_link_button("GitHub", "https://github.com/Armaan4477")
        layout.addWidget(armaan_github, 5, 1)

        armaan_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/armaan-nakhuda-756492235/")
        layout.addWidget(armaan_linkedin, 5, 2)

        # Nishal's row
        layout.addWidget(QLabel("Nishal Poojary", font=QFont("Arial", 18)), 3, 0)  # Increased font size
        nishal_github = self.create_link_button("GitHub", "https://github.com/Ailover123")
        layout.addWidget(nishal_github, 3, 1)

        nishal_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/nishal-poojary-159530290")
        layout.addWidget(nishal_linkedin, 3, 2)

        # Samay's row
        layout.addWidget(QLabel("Samay Pandey", font=QFont("Arial", 18)), 2, 0)  # Increased font size
        samay_github = self.create_link_button("GitHub", "https://github.com/ChampionSamay1644")
        layout.addWidget(samay_github, 2, 1)

        samay_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/samaypandey1644")
        layout.addWidget(samay_linkedin, 2, 2)

        # Urmi's row
        layout.addWidget(QLabel("Urmi Joshi", font=QFont("Arial", 18)), 4, 0)  # Increased font size
        urmi_github = self.create_link_button("GitHub", "https://github.com/ura-dev04")
        layout.addWidget(urmi_github, 4, 1)

        urmi_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/urmi-joshi-6697a7320/")
        layout.addWidget(urmi_linkedin, 4, 2)

        # Yash's row
        layout.addWidget(QLabel("Yash Patil", font=QFont("Arial", 18)), 6, 0)  # Increased font size
        yash_github = self.create_link_button("GitHub", "https://github.com/FrosT2k5")
        layout.addWidget(yash_github, 6, 1)

        yash_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/yash-patil-385171257")
        layout.addWidget(yash_linkedin, 6, 2)

        # Adwait's row
        layout.addWidget(QLabel("Adwait Patil", font=QFont("Arial", 18)), 7, 0)  # Increased font size
        adwait_github = self.create_link_button("GitHub", "https://github.com/Adwait0901")
        layout.addWidget(adwait_github, 7, 1)

        adwait_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/adwait-patil-56a1682a9/")
        layout.addWidget(adwait_linkedin, 7, 2)

        # Add extra space before the Project Documentation section
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), 8, 0, 1, 3)

        # Title 2: Project Documentation
        title_docs = QLabel("Project Documentation")
        title_docs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_docs.setFont(QFont("Arial", 16, QFont.Weight.Bold))  # Use consistent font
        layout.addWidget(title_docs, 9, 0, 1, 3)  # Span across 3 columns

        # Table Headers for Project Documentation
        layout.addWidget(QLabel("<b>Name</b>"), 10, 0)
        layout.addWidget(QLabel("<b>GitHub</b>"), 10, 1)
        layout.addWidget(QLabel("<b>LinkedIn</b>"), 10, 2)

        #samay's row
        layout.addWidget(QLabel("Samay Pandey", font=QFont("Arial", 18)), 11, 0)  # Increased font size
        samay_github = self.create_link_button("GitHub", "https://github.com/ChampionSamay1644")
        layout.addWidget(samay_github, 11, 1)

        samay_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/samaypandey1644")
        layout.addWidget(samay_linkedin, 11, 2)

        # XYZ's row (with placeholders)
        layout.addWidget(QLabel("Vedashree Gaikwad", font=QFont("Arial", 18)), 12, 0)  # Increased font size
        xyz_github = self.create_link_button("GitHub", "https://github.com/vedashree2004")  # Placeholder link
        layout.addWidget(xyz_github, 12, 1)

        xyz_linkedin = self.create_link_button("LinkedIn", "https://www.linkedin.com/in/vedashree-gaikwad-716783298")  # Placeholder link
        layout.addWidget(xyz_linkedin, 12, 2)

        # Close button at the bottom
        close_button = QPushButton("Close")
        self.style_button(close_button)  # Apply the style to the button
        layout.addWidget(close_button, 13, 0, 1, 3)  # Span across 3 columns

        self.setLayout(layout)

    def set_background(self):
        # Set a gradient background for the dialog
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
        button.setFixedSize(150, 40)  # Adjust the size as needed
        button.setFont(QFont("Arial", 12))
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(47, 54, 66, 255),   /* Dark Color */
                    stop: 1 rgba(75, 85, 98, 255)    /* Light Color */
                );
                color: white;
                border-radius: 12px;
                border: 2px solid rgba(0, 0, 0, 0.5);
                padding: 10px;
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

        # Adding a constant glow effect to the button
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)  # Adjust the blur radius for a softer glow
        glow_effect.setXOffset(0)       # Center the glow horizontally
        glow_effect.setYOffset(0)       # Center the glow vertically
        glow_effect.setColor(QColor(255, 255, 255, 100))  # Soft white glow with some transparency
        button.setGraphicsEffect(glow_effect)

    def create_link_button(self, text, url):
        button = QPushButton(text)
        self.style_button(button)  # Apply the style
        button.setStyleSheet(button.styleSheet() + "QPushButton { text-align: left; }")  # Align text to the left
        button.clicked.connect(lambda: self.open_link(url))  # Connect to link opening
        return button

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)  # Open the URL in the default web browser

# For testing the dialog directly
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CreditsDialog()
    dialog.exec()
