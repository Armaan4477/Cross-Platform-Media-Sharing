import sys
from PyQt6.QtWidgets import QDialog, QLabel, QGridLayout, QPushButton , QApplication
from PyQt6.QtCore import Qt

class CreditsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Credits")

        # Create layout for the dialog in grid form
        layout = QGridLayout()

        # Title 1: Coder/Debugger
        title_coder = QLabel("Coder/Debugger")
        title_coder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_coder, 0, 0, 1, 3)  # Span across 3 columns

        # Table Headers for Coder/Debugger
        layout.addWidget(QLabel("<b>Name</b>"), 1, 0)
        layout.addWidget(QLabel("<b>GitHub</b>"), 1, 1)
        layout.addWidget(QLabel("<b>LinkedIn</b>"), 1, 2)

        # Coder/Debugger - Alphabetical Order (Armaan, Nishal, Samay, Urmi, Yash)
        # Armaan's row
        layout.addWidget(QLabel("Armaan"), 2, 0)
        armaan_github = QLabel('<a href="https://github.com/Armaan4477">GitHub</a>')
        armaan_github.setOpenExternalLinks(True)
        layout.addWidget(armaan_github, 2, 1)

        armaan_linkedin = QLabel('<a href="https://www.linkedin.com/in/armaan-nakhuda-756492235/">LinkedIn</a>')
        armaan_linkedin.setOpenExternalLinks(True)
        layout.addWidget(armaan_linkedin, 2, 2)

        # Nishal's row
        layout.addWidget(QLabel("Nishal"), 3, 0)
        nishal_github = QLabel('<a href="https://github.com/Ailover123">GitHub</a>')
        nishal_github.setOpenExternalLinks(True)
        layout.addWidget(nishal_github, 3, 1)

        nishal_linkedin = QLabel('<a href="www.linkedin.com/in/nishal-poojary-159530290">LinkedIn</a>')
        nishal_linkedin.setOpenExternalLinks(True)
        layout.addWidget(nishal_linkedin, 3, 2)

        # Samay's row
        layout.addWidget(QLabel("Samay"), 4, 0)
        samay_github = QLabel('<a href="https://github.com/ChampionSamay1644">GitHub</a>')
        samay_github.setOpenExternalLinks(True)
        layout.addWidget(samay_github, 4, 1)

        samay_linkedin = QLabel('<a href="https://www.linkedin.com/in/samaypandey1644">LinkedIn</a>')
        samay_linkedin.setOpenExternalLinks(True)
        layout.addWidget(samay_linkedin, 4, 2)

        # Urmi's row
        layout.addWidget(QLabel("Urmi"), 5, 0)
        urmi_github = QLabel('<a href="https://github.com/ura-dev04">GitHub</a>')
        urmi_github.setOpenExternalLinks(True)
        layout.addWidget(urmi_github, 5, 1)

        urmi_linkedin = QLabel('<a href="https://www.linkedin.com/in/urmi-joshi-6697a7320/i">LinkedIn</a>')
        urmi_linkedin.setOpenExternalLinks(True)
        layout.addWidget(urmi_linkedin, 5, 2)

        # Yash's row
        layout.addWidget(QLabel("Yash"), 6, 0)
        yash_github = QLabel('<a href="https://github.com/FrosT2k5">GitHub</a>')
        yash_github.setOpenExternalLinks(True)
        layout.addWidget(yash_github, 6, 1)

        yash_linkedin = QLabel('<a href="https://www.linkedin.com/in/yash-patil-385171257">LinkedIn</a>')
        yash_linkedin.setOpenExternalLinks(True)
        layout.addWidget(yash_linkedin, 6, 2)

        # Title 2: Project Documentation
        title_docs = QLabel("Project Documentation")
        title_docs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_docs, 7, 0, 1, 3)  # Span across 3 columns

        # Table Headers for Project Documentation
        layout.addWidget(QLabel("<b>Name</b>"), 8, 0)
        layout.addWidget(QLabel("<b>GitHub</b>"), 8, 1)
        layout.addWidget(QLabel("<b>LinkedIn</b>"), 8, 2)

        # XYZ's row (with placeholders)
        layout.addWidget(QLabel("XYZ"), 9, 0)
        xyz_github = QLabel('<a href="#">GitHub (Placeholder)</a>')  # Placeholder link
        layout.addWidget(xyz_github, 9, 1)

        xyz_linkedin = QLabel('<a href="#">LinkedIn (Placeholder)</a>')  # Placeholder link
        layout.addWidget(xyz_linkedin, 9, 2)

        # Close button at the bottom
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, 10, 0, 1, 3)  # Span across 3 columns

        self.setLayout(layout)

# For testing the dialog directly
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CreditsDialog()
    dialog.exec()

