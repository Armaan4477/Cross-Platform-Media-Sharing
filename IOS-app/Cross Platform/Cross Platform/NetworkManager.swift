import Foundation
import Network
import Combine
import UIKit

class NetworkManager: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private var tcpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let tcpQueue = DispatchQueue(label: "TCPQueue")
    private let udpPort: NWEndpoint.Port = 12345
    private let tcpPort: NWEndpoint.Port = 12348
    private var connections: [NWConnection] = []

    init() {
        setupUDPListener()
        setupTCPListener()
    }

    private func setupUDPListener() {
        do {
            udpListener = try NWListener(using: .udp, on: udpPort)
            udpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewUDPConnection(connection)
            }
            udpListener?.start(queue: udpQueue)
        } catch {
            print("Failed to create UDP listener: \(error)")
        }
    }

    private func setupTCPListener() {
        do {
            tcpListener = try NWListener(using: .tcp, on: tcpPort)
            tcpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewTCPConnection(connection)
            }
            tcpListener?.start(queue: tcpQueue)
        } catch {
            print("Failed to create TCP listener: \(error)")
        }
    }

    private func handleNewUDPConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receiveMessage { [weak self] data, _, _, _ in
            guard let self = self, let data = data else { return }
            let message = String(data: data, encoding: .utf8)
            if message == "DISCOVER" {
                let response = "RECEIVER:\(UIDevice.current.name)"
                connection.send(content: response.data(using: .utf8), completion: .contentProcessed({ _ in }))
            }
        }
    }

    private func handleNewTCPConnection(_ connection: NWConnection) {
        connection.start(queue: tcpQueue)
        self.connections.append(connection)
        receiveFiles(connection)
    }

    private func receiveFiles(_ connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 4096) { [weak self] data, _, isComplete, error in
            guard let self = self, let data = data else { return }
            
            // Handle the received data, parse file information, etc.
            // This is a simplified example; you'll need to implement the complete file handling logic

            // Call receiveFiles again to keep receiving data
            if !isComplete {
                self.receiveFiles(connection)
            }
        }
    }

    func scanForDevices() {
        // This method can be used to initiate a scan, sending out a "DISCOVER" message to the network
        let connection = NWConnection(host: NWEndpoint.Host("255.255.255.255"), port: udpPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        connection.send(content: discoverMessage, completion: .contentProcessed({ _ in
            connection.cancel()
        }))
    }
}
