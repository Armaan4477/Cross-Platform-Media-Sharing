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
    private var broadcastIp: String?
    
    init() {
        self.broadcastIp = calculateBroadcastIp()  // Calculate the broadcast IP address on initialization
    }

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
        guard let broadcastIp = broadcastIp else {
            print("Broadcast IP is not available")
            return
        }
        let connection = NWConnection(host: NWEndpoint.Host(broadcastIp), port: listenPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        connection.send(content: discoverMessage, completion: .contentProcessed({ _ in
            connection.cancel()
        }))
    }
}
//test

private func calculateBroadcastIp() -> String? {
    var address: String?
    var ifaddr: UnsafeMutablePointer<ifaddrs>?
    
    if getifaddrs(&ifaddr) == 0 {
        var ptr = ifaddr
        while ptr != nil {
            defer { ptr = ptr?.pointee.ifa_next }
            
            guard let interface = ptr?.pointee else { continue }
            let addrFamily = interface.ifa_addr.pointee.sa_family
            
            if addrFamily == UInt8(AF_INET), let cString = interface.ifa_name {
                let name = String(cString: cString)
                if name == "en0" {  // Typically "en0" is the Wi-Fi interface on iOS
                    var addr = interface.ifa_addr.pointee
                    let ipAddress = withUnsafePointer(to: &addr) {
                        $0.withMemoryRebound(to: sockaddr_in.self, capacity: 1) {
                            String(cString: inet_ntoa($0.pointee.sin_addr))
                        }
                    }
                    address = ipAddress
                    break
                }
            }
        }
        freeifaddrs(ifaddr)
    }
    
    guard let localIp = address else { return nil }
    var ipParts = localIp.split(separator: ".")
    ipParts[3] = "255"
    return ipParts.joined(separator: ".")
}

