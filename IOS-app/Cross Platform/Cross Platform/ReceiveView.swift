import SwiftUI

struct ReceiveView: View {
    @EnvironmentObject var networkManager: NetworkManager

    var body: some View {
        VStack {
            Text("Waiting for file transfer")
                .font(.title)
                .padding()

            List(networkManager.devices, id: \.self) { device in
                Text(device)
            }
        }
        .onAppear {
            networkManager.setupUDPListener()
        }
    }
}

struct ReceiveView_Previews: PreviewProvider {
    static var previews: some View {
        ReceiveView()
            .environmentObject(NetworkManager())
    }
}
