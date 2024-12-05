import Foundation
import Network
import Combine
import UIKit

class ReceiverNetwork: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private var tcpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let tcpQueue = DispatchQueue(label: "TCPQueue")
    private let listenPort: NWEndpoint.Port = 12345
    private let responsePort: NWEndpoint.Port = 12346
    private let tcpPort: NWEndpoint.Port = 54314
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
        
        // Log the sent UDP response
        print("Sent UDP response: \(response)")
        
        // After sending "RECEIVER" response, start TCP listener for receiving JSON
        self.setupTCPListener()
    }
    
    private func setupTCPListener() {
            do {
                tcpListener = try NWListener(using: .tcp, on: tcpPort) // Updated to use tcpPort
                tcpListener?.newConnectionHandler = { [weak self] connection in
                    self?.handleNewTCPConnection(connection)
                }
                tcpListener?.start(queue: tcpQueue)
            } catch {
                print("Failed to create TCP listener: \(error)")
            }
        }

    private func handleNewTCPConnection(_ connection: NWConnection) {
        connection.start(queue: tcpQueue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 8) { [weak self] sizeData, _, isComplete, _ in
            guard let self = self, let sizeData = sizeData else { return }
            
            // Extract and log the size of the incoming JSON file
            let fileSize = sizeData.withUnsafeBytes { $0.load(as: UInt64.self) }
            print("Received JSON file size: \(fileSize) bytes")
            
            connection.receive(minimumIncompleteLength: Int(fileSize), maximumLength: Int(fileSize)) { [weak self] jsonData, _, isComplete, _ in
                guard let self = self, let jsonData = jsonData else { return }
                
                // Log received data
                print("Received raw JSON data: \(String(data: jsonData, encoding: .utf8) ?? "Invalid JSON")")
                
                if let json = try? JSONSerialization.jsonObject(with: jsonData, options: []) as? [String: Any] {
                    // Handle received JSON
                    self.handleReceivedJSON(json, connection: connection)
                }
                
                if isComplete {
                    connection.cancel()
                }
            }
        }
    }

    private func handleReceivedJSON(_ json: [String: Any], connection: NWConnection) {
        print("Received JSON: \(json)")
        guard let deviceType = json["device_type"] as? String else {
            print("Unknown device type received.")
            return
        }
        
        if deviceType == "python" {
            print("Connected to a Python device.")
            // Create response JSON
            let responseData: [String: Any] = [
                "device_type": "swift",
                "os": "ipad"
            ]
            
            if let jsonData = try? JSONSerialization.data(withJSONObject: responseData, options: []) {
                let jsonSize = UInt64(jsonData.count)
                let sizeData = withUnsafeBytes(of: jsonSize) { Data($0) }
                
                // Log the JSON data and size to be sent
                print("Sending JSON file size: \(jsonSize) bytes")
                print("Sending JSON response: \(responseData)")
                
                // Send size first
                connection.send(content: sizeData, completion: .contentProcessed({ error in
                    if let error = error {
                        print("Error sending size: \(error)")
                        return
                    }
                    
                    // Then send JSON data using the same connection
                    connection.send(content: jsonData, completion: .contentProcessed({ error in
                        if let error = error {
                            print("Error sending JSON: \(error)")
                        } else {
                            print("JSON response sent successfully")
                        }
                        // Keep connection open for a moment to ensure data is sent
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                            connection.cancel()
                        }
                    }))
                }))
            }
        } else {
            print("Unknown device type.")
            connection.cancel()
        }
    }

    private func sendJSONResponse(to endpoint: NWEndpoint) {
            guard case .hostPort(let host, _) = endpoint else {
                print("Failed to extract host from endpoint")
                return
            }

            let responseData: [String: Any] = [
                "device_type": "swift",
                "os": "ipados"
            ]
            
            if let jsonData = try? JSONSerialization.data(withJSONObject: responseData, options: []) {
                let jsonSize = UInt64(jsonData.count)
                let sizeData = withUnsafeBytes(of: jsonSize) { Data($0) }
                let responseConnection = NWConnection(host: host, port: tcpPort, using: .tcp) // Updated to use tcpPort
                responseConnection.start(queue: tcpQueue)
                
                print("Sending JSON file size: \(jsonSize) bytes")
                print("Sending JSON response: \(responseData)")
                
                responseConnection.send(content: sizeData, completion: .contentProcessed({ _ in
                    responseConnection.send(content: jsonData, completion: .contentProcessed({ _ in
                        responseConnection.cancel()
                    }))
                }))
            }
        }

    func scanForDevices() {
        guard let broadcastIp = broadcastIp else {
            print("Broadcast IP is not available")
            return
        }
        let connection = NWConnection(host: NWEndpoint.Host(broadcastIp), port: listenPort, using: .udp)
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        
        // Log the UDP discover message being sent
        print("Sending UDP discover message to \(broadcastIp)")
        
        connection.send(content: discoverMessage, completion: .contentProcessed({ _ in
            connection.cancel()
        }))
    }
}

// Helper function to calculate broadcast IP
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
