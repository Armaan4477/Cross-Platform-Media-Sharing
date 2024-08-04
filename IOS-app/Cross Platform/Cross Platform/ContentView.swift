import SwiftUI

struct ContentView: View {
    @EnvironmentObject var networkManager: NetworkManager

    var body: some View {
        VStack {
            Text("Cross Platform Data Sharing")
                .font(.largeTitle)
                .padding()

            Button(action: {
                networkManager.scanForDevices()
            }) {
                Text("Scan for Devices")
                    .font(.title)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }

            List(networkManager.devices, id: \.self) { device in
                Text(device)
            }
        }
        .padding()
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .environmentObject(NetworkManager())
    }
}
