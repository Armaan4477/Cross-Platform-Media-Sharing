import SwiftUI

struct ContentView: View {
    @State private var isReceiving = false

    var body: some View {
        VStack {
            Text("Cross Platform Data Sharing")
                .font(.largeTitle)
                .padding()

            if isReceiving {
                ReceiveView()
            } else {
                Button(action: {
                    // Action for sending data
                }) {
                    Text("Send")
                        .font(.title)
                        .padding()
                        .background(Color.green)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .padding(.bottom, 20)

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

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .environmentObject(ReceiverNetwork())
    }
}
