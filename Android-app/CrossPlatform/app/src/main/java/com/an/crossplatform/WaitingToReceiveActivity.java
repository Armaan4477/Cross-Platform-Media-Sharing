package com.an.crossplatform;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public class WaitingToReceiveActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345;
    private static final int SENDER_PORT = 12346;
    private static final int TCP_PORT = 12348; // Port for TCP connection
    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices

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
                        DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, senderAddress, SENDER_PORT);
                        socket.send(sendPacket);
                        Log.d("WaitingToReceive", "Sent RECEIVER message to: " + senderAddress.getHostAddress() + " on port " + SENDER_PORT);

                        // Start a new thread to handle TCP communication
                        new Thread(() -> establishTcpConnection(senderAddress)).start();
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private void establishTcpConnection(InetAddress senderAddress) {
        try (Socket socket = new Socket(senderAddress, TCP_PORT)) { // Ensure port is 12348
            // Prepare JSON data
            JSONObject json = new JSONObject();
            json.put("deviceName", DEVICE_NAME);
            json.put("deviceType", DEVICE_TYPE);
            byte[] sendData = json.toString().getBytes(StandardCharsets.UTF_8);

            // Send the JSON data size first
            DataOutputStream dos = new DataOutputStream(socket.getOutputStream());
            dos.writeLong(sendData.length); // Send the size of the JSON data
            dos.flush();

            // Send the JSON data
            dos.write(sendData);
            dos.flush();
            Log.d("WaitingToReceive", "Sent JSON data to: " + senderAddress.getHostAddress() + " on port " + TCP_PORT);

            // Receive the JSON data
            DataInputStream dis = new DataInputStream(socket.getInputStream());

            // Receive the size of the incoming JSON data
            long jsonSize = dis.readLong();
            byte[] recvBuf = new byte[(int) jsonSize]; // Allocate buffer based on the received size
            dis.readFully(recvBuf); // Read the JSON data into the buffer
            String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
            JSONObject receivedJson = new JSONObject(jsonStr);
            Log.d("WaitingToReceive", "Received JSON data: " + receivedJson.toString());

            // Call the receiveFile method with the received JSON data using intent
            Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
            intent.putExtra("receivedJson", receivedJson.toString());
            startActivity(intent);
        } catch (Exception e) {
            Log.e("WaitingToReceive", "Error during TCP connection", e);
        }
    }
}
