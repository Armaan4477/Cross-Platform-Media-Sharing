package com.an.crossplatform;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.net.SocketException;

public class WaitingToReceiveActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345; // Discovery port
    private static final int SENDER_PORT_JSON = 53000; // Response port for JSON on the Python app
    private static final int RECEIVER_PORT_JSON = 54000; // TCP port for Python app communication
    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices
    private int LISTEN_PORT = 12346;

    private boolean tcpConnectionEstablished = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        TextView txtWaiting = findViewById(R.id.txt_waiting);
        txtWaiting.setText("Waiting to receive file...");

        // Get the device name from config.json in the internal storage
        String rawJson = readJsonFromFile();
        if (rawJson != null) {
            try {
                JSONObject json = new JSONObject(rawJson);
                DEVICE_NAME = json.getString("device_name");  // Ensure correct key here
                Log.d("WaitingToReceive", "Device name from config: " + DEVICE_NAME);
            } catch (Exception e) {
                Log.e("WaitingToReceive", "Error parsing JSON", e);
                DEVICE_NAME = "Android Device";  // Fallback if error occurs
            }
        } else {
            DEVICE_NAME = "Android Device";  // Fallback if config.json doesn't exist
            Log.d("WaitingToReceive", "Using default device name: " + DEVICE_NAME);
        }

        // Start listening for discover messages
        startListeningForDiscover();
    }

    private String readJsonFromFile() {
        File folder = new File(getFilesDir(), "config");
        if (!folder.exists()) {
            Log.d("readJsonFromFile", "Config folder does not exist. Returning null.");
            return null;
        }

        File file = new File(folder, "config.json");
        Log.d("readJsonFromFile", "Looking for file at: " + file.getAbsolutePath());

        if (file.exists()) {
            Log.d("readJsonFromFile", "File exists. Reading contents...");
            StringBuilder jsonString = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file)))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                Log.d("readJsonFromFile", "File content: " + jsonString.toString());
                return jsonString.toString();
            } catch (Exception e) {
                Log.e("readJsonFromFile", "Error reading JSON from file", e);
            }
        } else {
            Log.d("readJsonFromFile", "File does not exist at: " + file.getAbsolutePath());
        }
        return null;
    }

    private void startListeningForDiscover() {
        new Thread(() -> {
            try (DatagramSocket socket = new DatagramSocket(UDP_PORT)) {
                byte[] recvBuf = new byte[15000];

                while (!tcpConnectionEstablished) { // Continue listening until a TCP connection is confirmed
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    socket.receive(receivePacket);

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

                        // Start a new thread to handle the TCP connection while still listening for discover messages
                        new Thread(() -> establishTcpConnection(senderAddress)).start();
                    }
                }
            } catch (Exception e) {
                Log.d("Error", "This is the error:" + e);
            }
        }).start();
    }

    private void establishTcpConnection(final InetAddress receiverAddress) {
        ServerSocket serverSocket = null; // Use ServerSocket for listening
        Socket socket = null;
        BufferedOutputStream outputStream = null;
        BufferedInputStream inputStream = null;
        Log.d("WaitingToReceive", "Establishing TCP connection with Sender");

        try {
            serverSocket = new ServerSocket(RECEIVER_PORT_JSON);  // Listening for incoming connections on RECEIVER_PORT_JSON
            Log.d("WaitingToReceive", "Waiting for incoming connections on port " + RECEIVER_PORT_JSON);

            while (true) { // Loop to handle multiple connections
                Log.d("WaitingToReceive", "Waiting for incoming connections...");
                socket = serverSocket.accept(); // Accept an incoming connection
                Log.d("WaitingToReceive", "Accepted connection from: " + socket.getInetAddress().toString());

                DataOutputStream bufferedOutputStream = new DataOutputStream(socket.getOutputStream());
                DataInputStream bufferedInputStream = new DataInputStream(socket.getInputStream());

                // Send JSON data first
                JSONObject deviceInfo = new JSONObject();
                deviceInfo.put("device_type", DEVICE_TYPE);
                deviceInfo.put("os", "Android");
                String deviceInfoStr = deviceInfo.toString();
                byte[] sendData = deviceInfoStr.getBytes(StandardCharsets.UTF_8);
                Log.d("WaitingToReceive", "Encoded JSON data size: " + sendData.length);

                // Convert the JSON size to little-endian bytes and send it first
                ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                sizeBuffer.putLong(sendData.length);
                bufferedOutputStream.write(sizeBuffer.array());
                bufferedOutputStream.flush();

                // Send the actual JSON data encoded in UTF-8
                bufferedOutputStream.write(sendData);
                bufferedOutputStream.flush();

                Log.d("WaitingToReceive", "Sent JSON data to receiver");

                // Start a thread to receive the JSON from the sender after sending
                Socket finalSocket = socket;
                new Thread(() -> {
                    try {
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

                        // If the received JSON is from the expected device, handle accordingly
                        if (receivedJson.getString("device_type").equals("python")) {
                            Log.d("WaitingToReceive", "Received JSON data from Python app");
                            // Proceed to the next activity (ReceiveFileActivityPython)
                            Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivityPython.class);
                            intent.putExtra("receivedJson", receivedJson.toString());
                            startActivity(intent);
                        } else if (receivedJson.getString("device_type").equals("java")) {
                            Log.d("WaitingToReceive", "Received JSON data from Java app");
                            // Proceed to the next activity (ReceiveFileActivity)
                            Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
                            intent.putExtra("receivedJson", receivedJson.toString());
                            startActivity(intent);
                        }
                    } catch (Exception e) {
                        Log.e("WaitingToReceive", "Error receiving JSON data", e);
                    } finally {
                        // Only close this specific socket after the entire communication is done
                        try {
                            if (bufferedInputStream != null) bufferedInputStream.close();
                            if (bufferedOutputStream != null) bufferedOutputStream.close();
                            if (finalSocket != null && !finalSocket.isClosed()) finalSocket.close();
                        } catch (IOException e) {
                            Log.e("WaitingToReceive", "Error closing socket resources", e);
                        }
                    }
                }).start();
            }
        } catch (Exception e) {
            Log.e("WaitingToReceive", "Error establishing TCP connection", e);
        } finally {
            // Make sure the serverSocket is only closed once we're done with all transactions
            try {
                if (serverSocket != null && !serverSocket.isClosed()) serverSocket.close();
            } catch (IOException e) {
                Log.e("WaitingToReceive", "Error closing ServerSocket", e);
            }
        }
    }
}