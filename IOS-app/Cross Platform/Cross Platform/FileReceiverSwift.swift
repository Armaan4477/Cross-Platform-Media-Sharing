import Foundation
import Network
import UIKit
import MobileCoreServices


protocol FileReceiverDelegate: AnyObject {
    func didUpdateProgress(_ progress: Double)
    func didReceiveFile(at url: URL)
    func didEncounterError(_ error: FileReceiverError)
}

enum FileReceiverError: Error {
    case listenerSetupFailed
    case connectionFailed
    case invalidData
    case fileWriteError
    case networkError(Error)
    case directoryError
}

@available(iOS 17.0, *)
actor FileReceiverSwift {
    private let port: NWEndpoint.Port = 57341
    private let queue = DispatchQueue(label: "FileReceiver", qos: .userInitiated)
    private var listener: NWListener?
    private var currentConnection: NWConnection?
    private let sharedContainer: URL
    @MainActor private weak var delegate: FileReceiverDelegate?
    
    @MainActor func setDelegate(_ delegate: FileReceiverDelegate) {
        self.delegate = delegate
    }
    
    init() throws {
        // Use the exact app group identifier you configured in Xcode
        guard let containerURL = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: "group.com.your.app.identifier" // Make sure this matches
        ) else {
            throw FileReceiverError.directoryError
        }
        
        let dataPath = containerURL.appendingPathComponent("DataDash", conformingTo: .folder)
        
        do {
            try FileManager.default.createDirectory(
                at: dataPath,
                withIntermediateDirectories: true,
                attributes: nil
            )
            
            try (dataPath as NSURL).setResourceValue(
                true,
                forKey: .isExcludedFromBackupKey
            )
            
            self.sharedContainer = dataPath
        } catch {
            throw FileReceiverError.directoryError
        }
    }
    
    
    func start() async throws {
        do {
            listener = try NWListener(using: .tcp, on: port)
            listener?.stateUpdateHandler = { [weak self] state in
                guard let self else { return }
                Task { await self.handleListenerState(state) }
            }
            
            listener?.newConnectionHandler = { [weak self] connection in
                guard let self else { return }
                Task { await self.handleNewConnection(connection) }
            }
            
            listener?.start(queue: queue)
        } catch {
            throw FileReceiverError.listenerSetupFailed
        }
    }
    
    private func handleListenerState(_ state: NWListener.State) async {
        switch state {
        case .ready:
            print("Listener ready on port 57341")
        case .failed(let error):
            await notifyDelegate { delegate in
                delegate.didEncounterError(.networkError(error))
            }
        default:
            break
        }
    }
    
    private func handleNewConnection(_ connection: NWConnection) async {
        currentConnection = connection
        connection.start(queue: queue)
        await receiveEncryptionFlag()
    }
    
    private func receiveEncryptionFlag() async {
        do {
            let data = try await receive(exactly: 8)
            guard let flag = String(data: data, encoding: .utf8) else {
                throw FileReceiverError.invalidData
            }
            
            if flag == "encyp: h" {
                currentConnection?.cancel()
                return
            }
            
            let isEncrypted = flag == "encyp: t"
            await receiveFileName(isEncrypted: isEncrypted)
        } catch {
            await notifyDelegate { delegate in
                delegate.didEncounterError(.networkError(error))
            }
        }
    }
    
    private func receiveFileName(isEncrypted: Bool) async {
        do {
            let sizeData = try await receive(exactly: 8)
            let nameLength = sizeData.withUnsafeBytes { $0.load(as: UInt64.self) }
            let nameData = try await receive(exactly: Int(nameLength))
            
            guard let fileName = String(data: nameData, encoding: .utf8) else {
                throw FileReceiverError.invalidData
            }
            
            await receiveFileSize(fileName: fileName, isEncrypted: isEncrypted)
        } catch {
            await notifyDelegate { delegate in
                delegate.didEncounterError(.networkError(error))
            }
        }
    }
    
    private func receiveFileSize(fileName: String, isEncrypted: Bool) async {
        do {
            let sizeData = try await receive(exactly: 8)
            let fileSize = sizeData.withUnsafeBytes { $0.load(as: UInt64.self) }
            await receiveFileContent(fileName: fileName, fileSize: fileSize, isEncrypted: isEncrypted)
        } catch {
            await notifyDelegate { delegate in
                delegate.didEncounterError(.networkError(error))
            }
        }
    }
    
    private func saveFileToSharedContainer(data: Data, fileName: String) throws -> URL {
        let fileURL = sharedContainer.appendingPathComponent(fileName)
        let coordinator = NSFileCoordinator()
        var coordError: NSError?
        var writeError: Error?
        
        coordinator.coordinate(
            writingItemAt: fileURL,
            options: .forReplacing,
            error: &coordError
        ) { url in
            do {
                try data.write(to: url, options: .atomic)
                try (url as NSURL).setResourceValue(
                    false,
                    forKey: .isExcludedFromBackupKey
                )
            } catch let error {
                writeError = error
            }
        }
        
        if let error = coordError ?? writeError {
            throw error
        }
        
        return fileURL
    }
    
    private func receiveFileContent(fileName: String, fileSize: UInt64, isEncrypted: Bool) async {
            var receivedData = Data()
            var receivedSize: UInt64 = 0
            
            do {
                while receivedSize < fileSize {
                    let chunkSize = min(4096, fileSize - receivedSize)
                    let data = try await receive(exactly: Int(chunkSize))
                    receivedData.append(data)
                    receivedSize += UInt64(data.count)
                    
                    let progress = Double(receivedSize) / Double(fileSize)
                    await notifyDelegate { delegate in
                        delegate.didUpdateProgress(progress)
                    }
                }
                
                // Save complete file
                let fileURL = try saveFileToSharedContainer(
                    data: receivedData,
                    fileName: fileName
                )
                
                await notifyDelegate { delegate in
                    delegate.didReceiveFile(at: fileURL)
                }
                
                await receiveEncryptionFlag()
                
            } catch {
                await notifyDelegate { delegate in
                    delegate.didEncounterError(.networkError(error))
                }
            }
        }
    
    private func receive(exactly length: Int) async throws -> Data {
        return try await withCheckedThrowingContinuation { continuation in
            currentConnection?.receive(minimumIncompleteLength: length, maximumLength: length) { content, _, isComplete, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                
                guard let data = content, data.count == length else {
                    continuation.resume(throwing: FileReceiverError.invalidData)
                    return
                }
                
                continuation.resume(returning: data)
            }
        }
    }
    
    private func notifyDelegate(_ action: @escaping (FileReceiverDelegate) -> Void) async {
        await MainActor.run {
            if let delegate = self.delegate {
                action(delegate)
            }
        }
    }
}
