import Foundation
import Network
import Combine
import UIKit

class ReceiverNetwork: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let udpPort: NWEndpoint.Port = 12345

    func setupUDPListener() {
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

    func scanForDevices() {
        let connection = NWConnection(host: NWEndpoint.Host("255.255.255.255"), port: udpPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        connection.send(content: discoverMessage, completion: .contentProcessed({ _ in
            connection.cancel()
        }))
    }
}
