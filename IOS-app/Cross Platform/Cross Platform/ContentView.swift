import SwiftUI

struct ContentView: View {
    @State private var isReceiving = false
    @State private var showSendView = false

    var body: some View {
        VStack {
            Text("Cross Platform Data Sharing")
                .font(.largeTitle)
                .padding()

            if isReceiving {
                ReceiveView()
            } else {
                Button(action: {
                    showSendView.toggle()
                }) {
                    Text("Send")
                        .font(.title)
                        .padding()
                        .background(Color.green)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .padding(.bottom, 20)
                .sheet(isPresented: $showSendView) {
                    SendView()
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

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
