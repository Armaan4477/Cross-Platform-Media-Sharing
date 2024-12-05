// FileReceiverView.swift
import SwiftUI
import Network
import Combine


struct FileReceiverView: View {
    @ObservedObject var viewModel: FileReceiverViewModel
    
    var body: some View {
        VStack {
            Text(viewModel.statusMessage)
                .padding()
            
            if viewModel.progress > 0 {
                ProgressView(value: viewModel.progress)
                    .padding()
            }
            
            List(viewModel.receivedFiles, id: \.self) { url in
                Text(url.lastPathComponent)
            }
        }
        .alert("Error", isPresented: $viewModel.isError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.statusMessage)
        }
    }
}

@available(iOS 17.0, *)
@MainActor
class FileReceiverViewModel: ObservableObject, FileReceiverDelegate {
    @Published var progress: Double = 0
    @Published var receivedFiles: [URL] = []
    @Published var statusMessage: String = "Waiting for connection..."
    @Published var isError: Bool = false
    
    private var fileReceiver: FileReceiverSwift?
    
    init() {
        setupReceiver()
    }
    
    private func setupReceiver() {
        Task {
            do {
                fileReceiver = try FileReceiverSwift()
                fileReceiver?.setDelegate(self) // Remove await since setDelegate isn't async
                try await fileReceiver?.start()
                statusMessage = "Ready to receive files"
            } catch {
                statusMessage = "Failed to start receiver: \(error.localizedDescription)"
                isError = true
            }
        }
    }
    
    // Make delegate methods nonisolated to comply with protocol
    nonisolated func didUpdateProgress(_ progress: Double) {
        // Dispatch to main actor since we're updating @Published properties
        Task { @MainActor in
            self.progress = progress
        }
    }
    
    nonisolated func didReceiveFile(at url: URL) {
        Task { @MainActor in
            self.receivedFiles.append(url)
            self.statusMessage = "Received file: \(url.lastPathComponent)"
            self.progress = 0
        }
    }
    
    nonisolated func didEncounterError(_ error: FileReceiverError) {
        Task { @MainActor in
            self.statusMessage = "Error: \(error.localizedDescription)"
            self.isError = true
        }
    }
}
