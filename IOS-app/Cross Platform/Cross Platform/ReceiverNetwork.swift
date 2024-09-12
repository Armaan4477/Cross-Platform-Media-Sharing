import Foundation
import Network
import Combine
import UIKit

class ReceiverNetwork: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let listenPort: NWEndpoint.Port = 12345
    private let responsePort: NWEndpoint.Port = 12346

    func setupUDPListener() {
        do {
            udpListener = try NWListener(using: .udp, on: listenPort)
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
                self.sendResponse(from: connection)
            }
        }
    }

    private func sendResponse(from connection: NWConnection) {
        // Determine the host from the endpoint
        guard case .hostPort(let host, _) = connection.endpoint else {
            print("Failed to extract host from connection endpoint")
            return
        }

        let response = "RECEIVER:\(UIDevice.current.name)"
        let responseConnection = NWConnection(host: host, port: responsePort, using: .udp)
        responseConnection.start(queue: udpQueue)
        responseConnection.send(content: response.data(using: .utf8), completion: .contentProcessed({ _ in
            responseConnection.cancel()
        }))
    }

    func scanForDevices() {
        let connection = NWConnection(host: NWEndpoint.Host("192.168.29.255"), port: listenPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        connection.send(content: discoverMessage, completion: .contentProcessed({ _ in
            connection.cancel()
        }))
    }
}
