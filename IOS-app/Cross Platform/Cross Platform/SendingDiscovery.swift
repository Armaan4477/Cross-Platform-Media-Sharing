import Foundation
import Network
import SwiftUI

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpPort: NWEndpoint.Port = 12345
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    
    func discoverDevices() {
        devices.removeAll()

        // Stop any previous listener if it exists
        udpListener?.cancel()

        // Start a UDP listener to listen for device responses
        do {
            udpListener = try NWListener(using: .udp, on: udpPort)
            udpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewConnection(connection)
            }
            udpListener?.start(queue: udpQueue)
            print("UDP Listener started on port \(udpPort.rawValue)")
        } catch {
            print("Failed to start UDP listener: \(error)")
            return
        }

        // Send the discovery message
        let connection = NWConnection(host: NWEndpoint.Host("255.255.255.255"), port: udpPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        connection.send(content: discoverMessage, completion: .contentProcessed { [weak self] error in
            if let error = error {
                print("Failed to send discovery message: \(error)")
            } else {
                print("Discovery message sent")
            }
            connection.cancel()
        })
    }

    private func handleNewConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let self = self else { return }
            if let error = error {
                print("Failed to receive data: \(error)")
                return
            }
            guard let data = data, isComplete else {
                if let data = data {
                    let message = String(data: data, encoding: .utf8) ?? "Invalid data"
                    print("Received incomplete or invalid data: \(message)")
                }
                return
            }
            let message = String(data: data, encoding: .utf8) ?? "Invalid data"
            print("Received message: \(message)")
            
            if message.hasPrefix("RECEIVER:") {
                let deviceName = message.replacingOccurrences(of: "RECEIVER:", with: "")
                DispatchQueue.main.async {
                    if !self.devices.contains(deviceName) {
                        self.devices.append(deviceName)
                        print("Discovered device: \(deviceName)")
                    }
                }
            }
        }
    }

    
    func connectToDevice(_ device: String) {
        // Implement connection logic to the selected device
        print("Connecting to \(device)")
        // Here you can implement the connection logic to the selected device
    }

    // Helper method to get device name
    private func getDeviceName() -> String {
        // Return the device name. Customize this as needed.
        return UIDevice.current.name
    }
}
