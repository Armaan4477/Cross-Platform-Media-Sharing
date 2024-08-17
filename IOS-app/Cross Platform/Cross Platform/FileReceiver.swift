import Foundation
import Network

class FileReceiver: ObservableObject {
    private var tcpListener: NWListener?
    private let tcpPort: NWEndpoint.Port = 12348
    private let queue = DispatchQueue(label: "FileReceiverQueue")
    
    init() {
        setupTCPListener()
    }
    
    func setupTCPListener() {
        do {
            tcpListener = try NWListener(using: .tcp, on: tcpPort)
            tcpListener?.newConnectionHandler = { [weak self] connection in
                self?.handleNewConnection(connection)
            }
            tcpListener?.start(queue: queue)
        } catch {
            print("Failed to create TCP listener: \(error)")
        }
    }
    
    private func handleNewConnection(_ connection: NWConnection) {
        connection.start(queue: queue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, _ in
            if let data = data {
                self?.handleData(data)
            }
            if isComplete {
                connection.cancel()
            }
        }
    }
    
    private func handleData(_ data: Data) {
        // Process received data and save files as needed
        // This is a placeholder implementation
        print("Received data: \(data)")
    }
    
    func start() {
        // Any additional setup or start operations
    }
    
    func stop() {
        tcpListener?.cancel()
    }
}
