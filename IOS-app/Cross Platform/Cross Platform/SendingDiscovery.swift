import Foundation
import Network
import Combine
import UIKit

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let udpPort: NWEndpoint.Port = 12345

    // Set up the UDP listener to listen for incoming messages
    func setupUDPListener() {
        stopUDPListener() // Stop any existing listener before starting a new one
        
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

    // Stop the UDP listener
    func stopUDPListener() {
        udpListener?.cancel()
        udpListener = nil
        print("UDP Listener stopped")
    }

    // Handle incoming UDP connections
    private func handleNewUDPConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receiveMessage { [weak self] data, _, _, error in
            guard let self = self else { return }
            if let error = error {
                print("Error receiving message: \(error.localizedDescription)")
                return
            }
            guard let data = data else {
                print("Received data is nil")
                return
            }
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
        let broadcastAddress = "255.255.255.255"
        let connection = NWConnection(host: NWEndpoint.Host(broadcastAddress), port: udpPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        
        connection.send(content: discoverMessage, completion: .contentProcessed { error in
            if let error = error {
                print("Failed to send DISCOVER message: \(error.localizedDescription)")
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
