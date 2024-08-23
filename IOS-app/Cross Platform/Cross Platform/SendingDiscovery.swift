import Foundation
import Network
import Combine

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let udpPort: NWEndpoint.Port = 12345
    private var isListening = false
    private var discoveryTimer: Timer?

    func startContinuousDiscovery() {
        if !isListening {
            setupUDPListener()
            isListening = true
        }

        discoveryTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.sendDiscoverMessage()
        }
    }

    func stopContinuousDiscovery() {
        discoveryTimer?.invalidate()
        discoveryTimer = nil
        isListening = false
        stopUDPListener()
    }

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

    func stopUDPListener() {
        udpListener?.cancel()
        udpListener = nil
        print("UDP Listener stopped")
    }

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
        // Add your connection logic here
        print("Connecting to device: \(device)")
    }

    private func handleNewUDPConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receiveMessage { [weak self] data, _, _, error in
            if let error = error {
                print("Error receiving message: \(error.localizedDescription)")
                return
            }
            guard let data = data, let message = String(data: data, encoding: .utf8) else { return }
            print("Received message: \(message)")

            if message.hasPrefix("RECEIVER:") {
                let deviceName = message.replacingOccurrences(of: "RECEIVER:", with: "")
                DispatchQueue.main.async {
                    if !self!.devices.contains(deviceName) {
                        self!.devices.append(deviceName)
                        print("Discovered device: \(deviceName)")
                    }
                }
            }
        }
    }
}
