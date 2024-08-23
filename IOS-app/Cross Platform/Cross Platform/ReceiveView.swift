import SwiftUI

struct ReceiveView: View {
    @EnvironmentObject var receiverNetwork: ReceiverNetwork

    var body: some View {
        VStack {
            Text("Waiting for file transfer")
                .font(.title)
                .padding()

            List(receiverNetwork.devices, id: \.self) { device in
                Text(device)
            }
        }
        .onAppear {
            receiverNetwork.setupUDPListener()
        }
    }
}

struct ReceiveView_Previews: PreviewProvider {
    static var previews: some View {
        ReceiveView()
            .environmentObject(ReceiverNetwork())
    }
}
