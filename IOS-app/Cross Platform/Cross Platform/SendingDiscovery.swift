import Foundation
import Network
import Combine

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let discoveryPort: NWEndpoint.Port = 12345  // Port for sending DISCOVER messages
    private let listeningPort: NWEndpoint.Port = 12346  // Port for listening to RECEIVER messages
    private var isListening = false
    private var discoveryTimer: Timer?
    private var broadcastIp: String?

    init() {
        self.broadcastIp = calculateBroadcastIp()  // Calculate the broadcast IP address on initialization
    }

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
            udpListener = try NWListener(using: .udp, on: listeningPort)  // Listen on port 12346
            udpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewUDPConnection(connection)
            }
            udpListener?.start(queue: udpQueue)
            print("UDP Listener started on port \(listeningPort.rawValue)")
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
        guard let broadcastIp = broadcastIp else {
            print("Broadcast IP is not available")
            return
        }
        print("Sending DISCOVER message to \(broadcastIp)")
        
        let connection = NWConnection(host: NWEndpoint.Host(broadcastIp), port: discoveryPort, using: .udp)  // Send on port 12345
        connection.start(queue: udpQueue)
        let discoverMessage = "DISCOVER".data(using: .utf8)
        
        connection.send(content: discoverMessage, completion: .contentProcessed { error in
            if let error = error {
                print("Failed to send DISCOVER message: \(error.localizedDescription)")
                connection.cancel()
            } else {
                print("DISCOVER message sent successfully")
                connection.cancel()
            }
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
}
