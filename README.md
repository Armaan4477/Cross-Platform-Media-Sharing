# DataDash

**DataDash** is an open-source, cross-platform data-sharing application designed for seamless, secure, and efficient file transfers. Whether you're using **Windows**, **Mac**, **Linux**, or **Android**, DataDash provides a reliable way to send files directly between devices without relying on the internet or third-party services.

---

## Key Features

- **Peer-to-Peer Connections**: No internet, no databases, no third-party involvement—your data stays private and secure.
- **Cross-Platform Support**: Compatible with Windows, Mac, Linux, and Android (iOS coming soon).
- **Encryption**: Optional password-protected transfers for added security.
- **TCP-Based Transfers**: Ensures complete, error-free file sharing.
- **User-Friendly Interface**: Intuitive design with simple options for sending, receiving, and configuring the app.
- **Open-Source**: Built for the community to use, contribute to, and improve.

---

## Tech Stack

- **Desktop**: Developed using **Python** and its libraries.
- **Android**: Built with **Java** and **XML**.
- **Website**: Created using **ReactJS**, focusing on dynamic UI and seamless user experience.

---

## Installation

### For Desktop (Windows/Mac/Linux):
1. Visit the [DataDash website](#).
2. Download the appropriate installer for your operating system.
3. Run the installer and follow the on-screen instructions.

### For Android:
1. Download the APK file from the [DataDash website](#).
2. Install the APK on your Android device (requires Android 11-14).

---

## How It Works

1. **Discover Devices**: The sender discovers available receivers on the network.
2. **Establish Connection**: A connection is created using JSON exchange, sharing metadata like IP address and OS type.
3. **Select Files**: The sender chooses files or folders to transfer. If encryption is enabled, a password is required.
4. **Transfer Process**: 
   - Metadata is sent first to the receiver.
   - Files are transferred using a Depth-First Search (DFS)-based logic over TCP.
   - The receiver processes incoming data using flags and tags to ensure proper structure and completeness.

---

## Screenshots

### Main Screen
![Main Screen](./Desktop-app/assets/readme%20img/python/mainscreenpy.jpg)

### Settings Menu
![Settings](./Desktop-app/assets/readme%20img/python/settingspy.jpg)

### iscovery
![File Transfer](./Desktop-app/assets/readme%20img/python/discoverypy.jpg)


---

## Credits

This project was made possible through the efforts of an incredible team:

- **Samay Pandey**: Project Lead.
- **Armaan Nakhuda** and **Yash Patil**: Co-developers.
- **Aarya Walve**: Website Design.
- **Special thanks** to **Urmi** and **Nishal Poojary** for their support.
- Additional thanks to everyone who contributed through testing, feedback, and UI/UX suggestions.

---

## Contributing

We welcome contributions! Feel free to fork the repository, create a branch, and submit a pull request. For major changes, please open an issue first to discuss your proposed changes.

---

## Connect

Have questions or suggestions? Reach out to us via [contact details](#) or create an issue here on GitHub.

---

**#DataDash #OpenSource #CrossPlatform #DataSharing #PeerToPeer #Encryption #TechInnovation #FileTransfer #ReactJS #Python #Java**
