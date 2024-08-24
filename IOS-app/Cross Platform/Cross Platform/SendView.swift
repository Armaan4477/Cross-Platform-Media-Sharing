import SwiftUI

struct SendView: View {
    @EnvironmentObject var sendingDiscovery: SendingDiscovery
    @State private var selectedDevice: String? = nil

    var body: some View {
        VStack {
            Button(action: {
                sendingDiscovery.startContinuousDiscovery()
            }) {
                Text("Discover Devices")
                    .font(.title)
                    .padding()
                    .background(Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding()

            List(sendingDiscovery.devices, id: \.self) { device in
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
                if let selectedDevice = selectedDevice {
                    sendingDiscovery.connectToDevice(selectedDevice)
                }
            }) {
                Text("Connect to Device")
                    .font(.title)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding()
            .disabled(selectedDevice == nil)

            Button(action: {
                sendingDiscovery.stopContinuousDiscovery()
            }) {
                Text("Stop Discovery")
                    .font(.title)
                    .padding()
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding()
        }
        .padding()
    }
}
