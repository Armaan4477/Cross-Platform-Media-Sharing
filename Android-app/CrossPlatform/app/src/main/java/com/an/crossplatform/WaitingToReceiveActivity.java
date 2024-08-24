package com.an.crossplatform;

import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

public class WaitingToReceiveActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345;
    private static final int senderPort = 12346;
    private String DEVICE_NAME;

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
            try {
                DatagramSocket socket = new DatagramSocket(UDP_PORT); // Ensure UDP_PORT is the port Android app uses for sending DISCOVER
                byte[] recvBuf = new byte[15000];

                while (true) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    socket.receive(receivePacket);

                    // Extract the raw data
                    byte[] rawData = receivePacket.getData();
                    int length = receivePacket.getLength();
                    String rawMessage = new String(rawData, 0, length).trim();

                    // Log the raw data and additional details
                    Log.d("WaitingToReceive", "Received raw message: " + rawMessage);
                    Log.d("WaitingToReceive", "Message length: " + length);
                    Log.d("WaitingToReceive", "Sender address: " + receivePacket.getAddress().getHostAddress());
                    Log.d("WaitingToReceive", "Sender port: " + receivePacket.getPort());


                    String message = new String(receivePacket.getData()).trim();
                    if (message.equals("DISCOVER")) {
                        InetAddress senderAddress = receivePacket.getAddress();
                        byte[] sendData = ("RECEIVER" + ":" + DEVICE_NAME).getBytes();
                        DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, senderAddress, senderPort); // Respond to senderPort
                        socket.send(sendPacket);
                        Log.d("WaitingToReceive", "Sent RECEIVE message to: " + senderAddress.getHostAddress() + " on port " + senderPort);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }
}
