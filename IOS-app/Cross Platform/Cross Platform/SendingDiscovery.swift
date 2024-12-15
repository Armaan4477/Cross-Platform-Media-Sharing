import Foundation
import Network
import Combine

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let discoveryPort: NWEndpoint.Port = 12345  // Port for sending DISCOVER messages
    private let listeningPort: NWEndpoint.Port = 12346  // Port for listening to RECEIVER messages
    private let SENDER_JSON_PORT: NWEndpoint.Port = 53000
    private let RECEIVER_JSON_PORT: NWEndpoint.Port = 54000
    private var isListening = false
    private var discoveryTimer: Timer?
    private var broadcastIp: String?
    private var tcpConnection: NWConnection?
    private var deviceInfo: [String: String]?
    private var connectionRetryCount = 0
    private let maxRetries = 3
    private var isConnecting = false

    init() {
        self.broadcastIp = calculateBroadcastIp()  // Calculate the broadcast IP address on initialization
    }

    func startContinuousDiscovery() {
        if !isListening {
            setupUDPListener()
            isListening = true
        }

        // Start the discovery timer
        discoveryTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.sendDiscoverMessage()
        }
    }

    func stopContinuousDiscovery() {
        // Invalidate the timer
        discoveryTimer?.invalidate()
        discoveryTimer = nil

        // Stop the UDP listener
        if isListening {
            stopUDPListener()
            isListening = false
        }
    }

    private func setupUDPListener() {
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

    private func stopUDPListener() {
        udpListener?.cancel()
        udpListener = nil
        print("UDP Listener stopped")
    }

    private func sendDiscoverMessage() {
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
        print("Connecting to device: \(device)")
        connectToReceiverTCP(ipAddress: device)
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
    
    func connectToReceiverTCP(ipAddress: String) {
        // Prepare device info
        deviceInfo = [
            "device_type": "swift",
            "os": "iOS"
        ]
        
        let endpoint = NWEndpoint.hostPort(host: .init(ipAddress), port: RECEIVER_JSON_PORT)
        tcpConnection = NWConnection(to: endpoint, using: .tcp)
        
        tcpConnection?.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                print("TCP Connection ready")
                self?.sendDeviceInfo()
            case .failed(let error):
                print("TCP Connection failed: \(error)")
            case .waiting(let error):
                print("TCP Connection waiting: \(error)")
            default:
                break
            }
        }
        
        tcpConnection?.start(queue: udpQueue)
    }

    private func sendDeviceInfo() {
        guard let deviceInfo = deviceInfo else { return }
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: deviceInfo)
            let size = UInt64(jsonData.count)
            var sizeData = withUnsafeBytes(of: size.littleEndian) { Data($0) }
            
            // Send size first
            tcpConnection?.send(content: sizeData, completion: .contentProcessed { error in
                if let error = error {
                    print("Failed to send size: \(error)")
                    return
                }
                
                // Then send JSON data
                self.tcpConnection?.send(content: jsonData, completion: .contentProcessed { error in
                    if let error = error {
                        print("Failed to send device info: \(error)")
                        return
                    }
                    
                    // Receive response device info
                    self.receiveDeviceInfo()
                })
            })
            
        } catch {
            print("Failed to serialize device info: \(error)")
        }
    }

    private func receiveDeviceInfo() {
        // Receive size first
        tcpConnection?.receive(minimumIncompleteLength: 8, maximumLength: 8) { [weak self] content, _, isComplete, error in
            guard let sizeData = content, sizeData.count == 8 else {
                print("Failed to receive size data")
                return
            }
            
            let size = sizeData.withUnsafeBytes { $0.load(as: UInt64.self).littleEndian }
            
            // Then receive JSON data
            self?.tcpConnection?.receive(minimumIncompleteLength: Int(size), maximumLength: Int(size)) { content, _, isComplete, error in
                guard let jsonData = content else {
                    print("Failed to receive device info")
                    return
                }
                
                do {
                    if let receivedInfo = try JSONSerialization.jsonObject(with: jsonData) as? [String: String] {
                        print("Received device info: \(receivedInfo)")
                        
                        // Handle device type
                        if receivedInfo["device_type"] == "python" {
                            print("Connected to Python device")
                            // Add your Python-specific handling here
                        } else if receivedInfo["device_type"] == "java" {
                            print("Connected to Java device")
                            // Add your Java-specific handling here
                        }
                    }
                } catch {
                    print("Failed to parse device info: \(error)")
                }
                
                // Close connection after exchange is complete
                self?.tcpConnection?.cancel()
            }
        }
    }
}
