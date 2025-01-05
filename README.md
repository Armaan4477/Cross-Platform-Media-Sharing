# 🚀DataDash - Cross-Platform Data Sharing App🚀

**DataDash** is an open-source, cross-platform data-sharing application designed for seamless, secure, and efficient file transfers. 

Whether you're using **Windows**, **Mac**, **Linux**, or **Android**, DataDash provides a reliable way to send files directly between devices without relying on the internet or third-party services.

---

## 🌟 Key Features 🌟

- 🔒  **Peer-to-Peer Connections**: No internet, no databases, no third-party involvement—your data stays private and secure.
- 📂 **Cross-Platform Support**: Compatible with Windows, Mac, Linux, and Android (iOS coming soon).
- 🔑   **Encryption**: Optional password-protected transfers for added security.
- 📡 **TCP-Based Transfers**: Ensures complete, error-free file sharing.
- 🖥 **User-Friendly Interface**: Intuitive design with simple options for sending, receiving, and configuring the app.
- 🌐 **Open-Source**: Built for the community to use, contribute to, and improve.

---

## ⚙ Tech Stack ⚙ 

- 💻 **Desktop**: Developed using **Python** and its libraries.
- 📱 **Android**: Built with **Java** and **XML**.
- 🌐 **Website**: Created using **ReactJS**, focusing on dynamic UI and seamless user experience.

---

## 🛠️Installation

#### For Desktop (Windows/Mac/Linux):
1. Visit the [DataDash website](https://datadashshare.vercel.app/download).
2. Download the appropriate installer for your operating system.
3. Run the installer and follow the on-screen instructions.

#### For Android:
1. Download the APK file from the [DataDash website](https://datadashshare.vercel.app/download).
2. Install the APK on your Android device (requires Android 11-14).

---

## 🎥  How It Works

1. **Discover Devices**: The sender discovers available receivers on the network.
2. **Establish Connection**: A connection is created using JSON exchange, sharing metadata like IP address and OS type.
3. **Select Files**: The sender chooses files or folders to transfer. If encryption is enabled, a password is required.
4. **Transfer Process**: 
   - Metadata is sent first to the receiver.
   - Files are transferred using a Depth-First Search (DFS)-based logic over TCP.
   - The receiver processes incoming data using flags and tags to ensure proper structure and completeness.

---


## 🔖 Credits

This project was made possible through the efforts of an incredible team:

-  **Armaan Nakhuda** , **Samay Pandey** and **Yash Patil**: Project Developers.
- **Aarya Walve**: Website Developer.
- **Special thanks** to **Adwait Patil** , **Nishal Poojary** and **Urmi Joshi** and  for their support.
- Additional thanks to everyone who contributed through testing, feedback, and UI/UX suggestions.

---

## 🌱 App results

  <table align-items="center" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 800px; margin: 20px auto; background-color: #ffffff;">
  <thead>
    <tr>
      <th text-items="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">Main Menu</th>
      <th text-align="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">Discovery</th>
      <th text-align="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">File Sending</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td text-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="./Desktop-app/assets/readme img/screenshots/screenshots/mac/main menu.png" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
      </td>
      <td text-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="./Desktop-app/assets/readme img/screenshots/screenshots/mac/discovery.png" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
      </td>
      <td text-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="./Desktop-app/assets/readme img/screenshots/screenshots/mac/file sending.png" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
      </td>
    </tr>
  </tbody>
  <!--<thead>
    <tr>
      <th text-align ="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">Discovery</th>
      <th text-align="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">Waiting for Sender</th>
      <th text-align="center" style="padding: 12px; background-color: #f6f8fa; border: 1px solid #ddd; font-size: 16px; font-weight: 600;">Image Title 6</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td text-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="./Desktop-app/assets/readme img/screenshots/screenshots/mac/discovery.png" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
        <p style="margin: 10px 0; color: #666; font-size: 14px;">Description for image 4</p>
      </td>
      <td text-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="path/to/image5.jpg" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
        <p style="margin: 10px 0; color: #666; font-size: 14px;">Description for image 5</p>
      </td>
      <td tetx-align="center" style="padding: 15px; border: 1px solid #ddd; vertical-align: top;">
        <img src="path/to/image6.jpg" width="200" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
        <p style="margin: 10px 0; color: #666; font-size: 14px;">Description for image 6</p>
      </td>
    </tr>
  </tbody>--->
</table>
---
## 🌱 Contributing

We welcome contributions! Feel free to fork the repository, create a branch, and submit a pull request. For major changes, please open an issue first to discuss your proposed changes.

---

## 🤝 Connect

Have questions or suggestions? Reach out to us via [our website](https://datadashshare.vercel.app/feedback) or create an issue here on GitHub.

---

