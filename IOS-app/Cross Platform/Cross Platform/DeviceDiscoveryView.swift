import SwiftUI

struct DeviceDiscoveryView: View {
    @ObservedObject var networkManager: NetworkManager
    @State private var discoveredDevices: [String] = []
    @State private var selectedDevice: String?
    @State private var isConnecting = false

    var body: some View {
        VStack {
            Text("Discover Devices")
                .font(.title)
                .padding()

            Button(action: {
                networkManager.scanForDevices()
            }) {
                Text("Discover")
                    .font(.title)
                    .padding()
                    .background(Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding(.bottom, 20)

            List(discoveredDevices, id: \.self) { device in
                HStack {
                    Text(device)
                    Spacer()
                    if device == selectedDevice {
                        Image(systemName: "checkmark")
                    }
                }
                .contentShape(Rectangle())
                .onTapGesture {
                    selectedDevice = device
                }
            }

            Button(action: {
                if let device = selectedDevice {
                    // Implement the connection logic here
                    isConnecting = true
                }
            }) {
                Text("Connect")
                    .font(.title)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .disabled(selectedDevice == nil)
        }
        .onReceive(networkManager.$devices) { devices in
            self.discoveredDevices = devices
        }
        .padding()
        .alert(isPresented: $isConnecting) {
            Alert(title: Text("Connecting"), message: Text("Connecting to \(selectedDevice ?? "")"), dismissButton: .default(Text("OK")))
        }
    }
}

struct DeviceDiscoveryView_Previews: PreviewProvider {
    static var previews: some View {
        DeviceDiscoveryView(networkManager: NetworkManager())
    }
}
