package com.an.crossplatform;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

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
                    // Call the establishTcpConnection method repeatedly for 15 seconds
                        long startTime = System.currentTimeMillis();
                        while (System.currentTimeMillis() - startTime < 15000) {
                            // Pause the thread until tcp connection is established
                            Thread.sleep(150);
                            establishTcpConnection(receivePacket.getAddress());
                        }
                    }
                }
            } catch (Exception e) {
                Log.d("Error", "This is the error:" + e);
            }
        }).start();
    }

    private void establishTcpConnection(final InetAddress receiverAddress) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                Socket socket = null;
                BufferedOutputStream outputStream = null;
                BufferedInputStream inputStream = null;

                try {
                    // Create a new Socket to connect to the receiver with IPv4 address
                    socket = new Socket();
                    socket.bind(new InetSocketAddress(RECEIVER_PORT_JSON));
                    socket.connect(new InetSocketAddress(receiverAddress, SENDER_PORT_JSON), 10000);

                    // Prepare JSON data to send (Android device info)
                    JSONObject deviceInfo = new JSONObject();
                    deviceInfo.put("device_type", DEVICE_TYPE);
                    deviceInfo.put("os", "Android");
                    String deviceInfoStr = deviceInfo.toString();
                    byte[] sendData = deviceInfoStr.getBytes(StandardCharsets.UTF_8);
                    Log.d("WaitingToReceive", "Encoded JSON data size: " + sendData.length);

                    DataOutputStream bufferedOutputStream = new DataOutputStream(socket.getOutputStream());
                    DataInputStream bufferedInputStream = new DataInputStream(socket.getInputStream());

                    // Convert the JSON size to little-endian bytes and send it first
                    ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                    sizeBuffer.putLong(sendData.length);
                    bufferedOutputStream.write(sizeBuffer.array());
                    bufferedOutputStream.flush();

                    // Send the actual JSON data encoded in UTF-8
                    bufferedOutputStream.write(sendData);
                    bufferedOutputStream.flush();

                    // Read the JSON size first (as a long, little-endian)
                    byte[] recvSizeBuf = new byte[Long.BYTES];
                    bufferedInputStream.read(recvSizeBuf);
                    ByteBuffer sizeBufferReceived = ByteBuffer.wrap(recvSizeBuf).order(ByteOrder.LITTLE_ENDIAN);
                    long jsonSize = sizeBufferReceived.getLong();

                    // Read the actual JSON data
                    byte[] recvBuf = new byte[(int) jsonSize];
                    int totalBytesRead = 0;
                    while (totalBytesRead < recvBuf.length) {
                        int bytesRead = bufferedInputStream.read(recvBuf, totalBytesRead, recvBuf.length - totalBytesRead);
                        if (bytesRead == -1) {
                            throw new IOException("End of stream reached before reading complete data");
                        }
                        totalBytesRead += bytesRead;
                    }

                    // Convert the received bytes into a JSON string
                    String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
                    JSONObject receivedJson = new JSONObject(jsonStr);
                    Log.d("WaitingToReceive", "Received JSON data: " + receivedJson.toString());
                    if (receivedJson.getString("device_type").equals("python")) {
                        Log.d("WaitingToReceive", "Received JSON data from Python app");
                    }
                    else if (receivedJson.getString("device_type").equals("java")) {
                        Log.d("WaitingToReceive", "Received JSON data from Java app");
                        // Proceed to the next activity (ReceiveFileActivity)
                        Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
                        intent.putExtra("receivedJson", receivedJson.toString());
                        startActivity(intent);
                    }

                } catch (Exception ignored) {
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
        }).start();
    }
}
