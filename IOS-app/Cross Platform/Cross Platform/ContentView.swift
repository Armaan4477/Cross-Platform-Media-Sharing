import SwiftUI

struct ContentView: View {
    @State private var isReceiving = false
    @State private var showDiscoveryView = false
    @StateObject private var networkManager = NetworkManager()

    var body: some View {
        NavigationView {
            VStack {
                Text("Cross Platform Data Sharing")
                    .font(.largeTitle)
                    .padding()

                if isReceiving {
                    ReceiveView()
                } else {
                    NavigationLink(
                        destination: DeviceDiscoveryView(networkManager: networkManager),
                        isActive: $showDiscoveryView
                    ) {
                        Button(action: {
                            showDiscoveryView = true
                        }) {
                            Text("Send")
                                .font(.title)
                                .padding()
                                .background(Color.green)
                                .foregroundColor(.white)
                                .cornerRadius(10)
                        }
                        .padding(.bottom, 20)
                    }

                    Button(action: {
                        isReceiving = true
                    }) {
                        Text("Receive")
                            .font(.title)
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
            }
            .padding()
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
