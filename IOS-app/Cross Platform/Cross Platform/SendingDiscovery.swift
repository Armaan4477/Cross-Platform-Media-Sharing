import Foundation
import Network
import Combine
import UIKit

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = [] // List of discovered devices
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let udpPort: NWEndpoint.Port = 12345 // Port for UDP communication

    // Set up the UDP listener to listen for incoming messages
    func setupUDPListener() {
        do {
            udpListener = try NWListener(using: .udp, on: udpPort)
            udpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewUDPConnection(connection)
            }
            udpListener?.start(queue: udpQueue)
            print("UDP Listener started on port \(udpPort.rawValue)")
        } catch {
            print("Failed to create UDP listener: \(error)")
        }
    }

    // Handle incoming UDP connections
    private func handleNewUDPConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receiveMessage { [weak self] data, _, _, _ in
            guard let self = self else { return }
            guard let data = data else { return }
            let message = String(data: data, encoding: .utf8) ?? "Invalid data"
            print("Received message: \(message)")

            // Check if the message starts with "RECEIVER:"
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

    // Send a DISCOVER message
    func sendDiscoverMessage() {
        print("Sending DISCOVER message")
        let connection = NWConnection(host: NWEndpoint.Host("255.255.255.255"), port: udpPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        
        connection.send(content: discoverMessage, completion: .contentProcessed { error in
            if let error = error {
                print("Failed to send DISCOVER message: \(error)")
            } else {
                print("DISCOVER message sent successfully")
            }
            connection.cancel()
        })
    }

    func connectToDevice(_ device: String) {
        // Implement connection logic to the selected device
        print("Connecting to \(device)")
        // Here you can implement the connection logic to the selected device
    }
}
