package com.an.crossplatform;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;

public class WaitingToReceiveActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345; // Discovery port on Android
    private static final int SENDER_PORT_JSON = 53000; // Response port for JSON on Python app
    private static final int RECEIVER_PORT_JSON = 54000; // TCP port for Python app communication
    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices
    private int LISTEN_PORT = 12346;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        TextView txtWaiting = findViewById(R.id.txt_waiting);
        txtWaiting.setText("Waiting to receive file...");

        // Get the device name
        DEVICE_NAME = Build.MODEL;

        startListeningForDiscover();
    }

    private void startListeningForDiscover() {
        new Thread(() -> {
            try (DatagramSocket socket = new DatagramSocket(UDP_PORT)) {
                byte[] recvBuf = new byte[15000];

                while (true) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    socket.receive(receivePacket);

                    // Extract the raw data
                    String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();

                    Log.d("WaitingToReceive", "Received raw message: " + message);
                    Log.d("WaitingToReceive", "Sender address: " + receivePacket.getAddress().getHostAddress());
                    Log.d("WaitingToReceive", "Sender port: " + receivePacket.getPort());

                    if (message.equals("DISCOVER")) {
                        InetAddress senderAddress = receivePacket.getAddress();
                        byte[] sendData = ("RECEIVER:" + DEVICE_NAME).getBytes();
                        DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, senderAddress, LISTEN_PORT);
                        socket.send(sendPacket);
                        Log.d("WaitingToReceive", "Sent RECEIVER message to: " + senderAddress.getHostAddress() + " on port " + LISTEN_PORT);

                        // Handle TCP communication without using a separate thread
                        // Stop listening for discover messages
                        establishTcpConnection(senderAddress);
                    }
                }
            } catch (Exception e) {
                Log.d("Error", "This is the error:" + e);
            }
        }).start();
    }

    private void establishTcpConnection(InetAddress receiverAddress) {
        Socket socket = null;
        BufferedOutputStream outputStream = null;
        BufferedInputStream inputStream = null;

        try {
            // Create a new Socket to connect to the receiver
            socket = new Socket(receiverAddress, SENDER_PORT_JSON);

            // Prepare JSON data to send (Android device info)
            JSONObject deviceInfo = new JSONObject();
            deviceInfo.put("device_type", DEVICE_TYPE);
            deviceInfo.put("os", "Android");
            byte[] sendData = deviceInfo.toString().getBytes(StandardCharsets.UTF_8);

            // Send the JSON data size first (as a long)
            OutputStream rawOutputStream = socket.getOutputStream();
            BufferedOutputStream bufferedOutputStream = new BufferedOutputStream(rawOutputStream);
            bufferedOutputStream.write(ByteBuffer.allocate(Long.BYTES).putLong(sendData.length).array());
            bufferedOutputStream.flush();

            // Send the actual JSON data
            bufferedOutputStream.write(sendData);
            bufferedOutputStream.flush();

            // Read the JSON size first (as a long)
            InputStream rawInputStream = socket.getInputStream();
            BufferedInputStream bufferedInputStream = new BufferedInputStream(rawInputStream);
            byte[] recvSizeBuf = new byte[Long.BYTES];
            bufferedInputStream.read(recvSizeBuf);
            ByteBuffer sizeBufferReceived = ByteBuffer.wrap(recvSizeBuf);
            long jsonSize = sizeBufferReceived.getLong();

            // Read the actual JSON data
            byte[] recvBuf = new byte[(int) jsonSize];
            bufferedInputStream.read(recvBuf);

            // Convert the received bytes into a JSON string
            String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
            JSONObject receivedJson = new JSONObject(jsonStr);
            Log.d("WaitingToReceive", "Received JSON data: " + receivedJson.toString());

            // Proceed to the next activity (ReceiveFileActivity)
            Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
            intent.putExtra("receivedJson", receivedJson.toString());
            startActivity(intent);

        } catch (Exception e) {
            Log.e("WaitingToReceive", "Error during TCP communication", e);
        } finally {
            // Close resources
            try {
                if (inputStream != null) inputStream.close();
                if (outputStream != null) outputStream.close();
                if (socket != null) socket.close();
            } catch (IOException e) {
                Log.e("WaitingToReceive", "Error closing resources", e);
            }
        }
    }
}
