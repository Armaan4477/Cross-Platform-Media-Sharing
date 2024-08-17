import Foundation
import Network
import SwiftUI

class SendingDiscovery: ObservableObject {
    @Published var devices: [String] = []
    private var udpListener: NWListener?
    private let udpQueue = DispatchQueue(label: "UDPQueue")
    private let port: NWEndpoint.Port = 12345
    
    func discoverDevices() {
        devices.removeAll()
        
        // Stop any previous listener if it exists
        udpListener?.cancel()
        udpListener = nil
        
        // Start a UDP listener to listen for device responses on port 12345
        do {
            udpListener = try NWListener(using: .udp, on: port)
            udpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewConnection(connection)
            }
            udpListener?.start(queue: udpQueue)
            print("UDP Listener started on port \(port.rawValue)")
        } catch {
            print("Failed to start UDP listener: \(error)")
            return
        }
        
        // Print IP Address of the device
        print("Device IP Address: \(getDeviceIPAddress())")
        
        // Send the discovery message
        sendDiscoveryMessage()
    }
    
    private func sendDiscoveryMessage() {
        print("Attempting to send discovery message")
                
                let connection = NWConnection(host: NWEndpoint.Host("255.255.255.255"), port: port, using: .udp)
                connection.start(queue: udpQueue)
                
                let discoverMessage = "RECEIVER:\(UIDevice.current.name)".data(using: .utf8)
                connection.send(content: discoverMessage, completion: .contentProcessed { error in
                    if let error = error {
                        print("Failed to send discovery message: \(error)")
                    } else {
                        print("Discovery message sent successfully")
                    }
                    connection.cancel()
                })
    }

    
    private func handleNewConnection(_ connection: NWConnection) {
        connection.start(queue: udpQueue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let self = self else { return }
            if let error = error {
                print("Failed to receive data: \(error)")
                return
            }
            guard let data = data, isComplete else {
                if let data = data {
                    let message = String(data: data, encoding: .utf8) ?? "Invalid data"
                    print("Received incomplete or invalid data: \(message)")
                }
                return
            }
            let message = String(data: data, encoding: .utf8) ?? "Invalid data"
            print("Received message: \(message)")
            
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
    
    func connectToDevice(_ device: String) {
        // Implement connection logic to the selected device
        print("Connecting to \(device)")
        // Here you can implement the connection logic to the selected device
    }
    
    // Helper method to get device IP address
    private func getDeviceIPAddress() -> String {
        // Get the IP address of the device
        var ipAddress = "Unknown"
        if let addresses = getWiFiAddresses(), let address = addresses.first {
            ipAddress = address
        }
        return ipAddress
    }
    
    // Helper method to get Wi-Fi IP addresses
    private func getWiFiAddresses() -> [String]? {
        var addresses: [String] = []
        var ifaddr: UnsafeMutablePointer<ifaddrs>? = nil
        if getifaddrs(&ifaddr) == 0 {
            var ptr = ifaddr
            while ptr != nil {
                defer { ptr = ptr?.pointee.ifa_next }
                let interface = ptr!.pointee
                let addrFamily = interface.ifa_addr.pointee.sa_family
                if addrFamily == UInt8(AF_INET) || addrFamily == UInt8(AF_INET6) {
                    let name = String(cString: interface.ifa_name)
                    if name == "en0" { // Wi-Fi interface
                        var addr = interface.ifa_addr.pointee
                        var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                        if getnameinfo(&addr, socklen_t(interface.ifa_addr.pointee.sa_len), &hostname, socklen_t(hostname.count), nil, 0, NI_NUMERICHOST) == 0 {
                            addresses.append(String(cString: hostname))
                        }
                    }
                }
            }
            freeifaddrs(ifaddr)
        }
        return addresses
    }
}
