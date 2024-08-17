import SwiftUI

struct ReceiveView: View {
    @StateObject private var fileReceiver = FileReceiver()

    var body: some View {
        VStack {
            Text("Receiving Files")
                .font(.title)
                .padding()

            // Here, you can add progress indicators or other UI elements related to receiving files

            Button(action: {
                // Trigger file reception process here
                fileReceiver.start() // Start the file receiving process
            }) {
                Text("Start Receiving")
                    .font(.title)
                    .padding()
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding(.bottom, 20)
        }
        .onAppear {
            fileReceiver.start() // Ensure file receiving starts when the view appears
        }
        .onDisappear {
            fileReceiver.stop() // Optionally stop the receiver when the view disappears
        }
    }
}

struct ReceiveView_Previews: PreviewProvider {
    static var previews: some View {
        ReceiveView()
    }
}
