package com.an.crossplatform;

import android.content.Intent;
import android.os.Bundle;
import android.os.Environment;
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
import androidx.activity.OnBackPressedCallback;

public class WaitingToReceiveActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345; // Discovery port

    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices
    private static final int JSON_EXCHANGE_PORT = 54314;
    private int LISTEN_PORT = 12346;
    private ServerSocket serverSocket;
    private DatagramSocket udpSocket;
    private Socket clientSocket;
    private DataInputStream bufferedInputStream;
    private DataOutputStream bufferedOutputStream;
    private volatile boolean isRunning = true;

    private boolean tcpConnectionEstablished = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                closeAllSockets();
            }
        });

        TextView txtWaiting = findViewById(R.id.txt_waiting);
        txtWaiting.setText("Waiting to connect to sender...");

        // Get the device name from config.json in the internal storage
        String rawJson = readJsonFromFile();
        if (rawJson != null) {
            try {
                JSONObject json = new JSONObject(rawJson);
                DEVICE_NAME = json.getString("device_name");  // Ensure correct key here
                FileLogger.log("WaitingToReceive", "Device name from config: " + DEVICE_NAME);
            } catch (Exception e) {
                FileLogger.log("WaitingToReceive", "Error parsing JSON", e);
                DEVICE_NAME = "Android Device";  // Fallback if error occurs
            }
        } else {
            DEVICE_NAME = "Android Device";  // Fallback if config.json doesn't exist
            FileLogger.log("WaitingToReceive", "Using default device name: " + DEVICE_NAME);
        }

        // Start listening for discover messages
        startListeningForDiscover();
    }

    private String readJsonFromFile() {
        // Access the config.json file in the new location in Downloads/DataDash/Config
        File folder = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config/");
        if (!folder.exists()) {
            FileLogger.log("readJsonFromFile", "Config folder does not exist in Downloads. Returning null.");
            return null;
        }

        File file = new File(folder, "config.json");
        FileLogger.log("readJsonFromFile", "Looking for config file at: " + file.getAbsolutePath());

        if (file.exists()) {
            FileLogger.log("readJsonFromFile", "File exists. Reading contents...");
            StringBuilder jsonString = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file)))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                FileLogger.log("readJsonFromFile", "File content: " + jsonString.toString());
                return jsonString.toString();
            } catch (Exception e) {
                FileLogger.log("readJsonFromFile", "Error reading JSON from file", e);
            }
        } else {
            FileLogger.log("readJsonFromFile", "Config file does not exist at: " + file.getAbsolutePath());
        }
        return null;
    }

    private void startListeningForDiscover() {
        new Thread(() -> {
            try {
                udpSocket = new DatagramSocket(UDP_PORT);
                udpSocket.setSoTimeout(1000); // 1 second timeout
                byte[] recvBuf = new byte[15000];

                while (!tcpConnectionEstablished) { // Remove isRunning check here
                    try {
                        DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                        FileLogger.log("WaitingToReceive", "Waiting for discovery packet...");
                        udpSocket.receive(receivePacket);

                        String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();
                        FileLogger.log("WaitingToReceive", "Received message: " + message);

                        if (message.equals("DISCOVER")) {
                            InetAddress senderAddress = receivePacket.getAddress();
                            byte[] sendData = ("RECEIVER:" + DEVICE_NAME).getBytes();
                            DatagramPacket sendPacket = new DatagramPacket(
                                    sendData,
                                    sendData.length,
                                    senderAddress,
                                    LISTEN_PORT
                            );
                            udpSocket.send(sendPacket);
                            FileLogger.log("WaitingToReceive", "Sent RECEIVER response to: " +
                                    senderAddress.getHostAddress() + ":" + LISTEN_PORT);

                            // Start TCP connection in new thread
                            new Thread(() -> establishTcpConnection(senderAddress)).start();
                        }
                    } catch (SocketException e) {
                        if (!isRunning) {
                            FileLogger.log("WaitingToReceive", "UDP socket closed normally");
                            break;
                        }
                    } catch (IOException e) {
                        // Timeout - continue listening
                        continue;
                    }
                }
            } catch (Exception e) {
                FileLogger.log("WaitingToReceive", "UDP Discovery error", e);
            }
        }).start();
    }

    private void closeAllSockets() {
        if (!isRunning) {
            return; // Prevent multiple closes
        }
        isRunning = false;

        try {
            // Close UDP socket
            if (udpSocket != null && !udpSocket.isClosed()) {
                udpSocket.close();
                udpSocket = null;
                FileLogger.log("WaitingToReceive", "UDP socket closed");
            }

            // Close TCP related resources
            if (bufferedInputStream != null) {
                bufferedInputStream.close();
                bufferedInputStream = null;
            }
            if (bufferedOutputStream != null) {
                bufferedOutputStream.close();
                bufferedOutputStream = null;
            }
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
                clientSocket = null;
            }
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
                serverSocket = null;
            }

            tcpConnectionEstablished = true; // Ensure discovery stops
            FileLogger.log("WaitingToReceive", "All sockets closed successfully");

        } catch (IOException e) {
            FileLogger.log("WaitingToReceive", "Error closing sockets", e);
        } finally {
            finish(); // Close the activity
        }
    }

    private void establishTcpConnection(final InetAddress receiverAddress) {
        ServerSocket serverSocket = null;
        Socket socket = null;

        try {
            // Listen only on port 54000
            serverSocket = new ServerSocket(JSON_EXCHANGE_PORT);
            FileLogger.log("WaitingToReceive", "Waiting for incoming connections on port " + JSON_EXCHANGE_PORT);

            socket = serverSocket.accept();
            FileLogger.log("WaitingToReceive", "Accepted connection from: " + socket.getInetAddress());

            DataOutputStream bufferedOutputStream = new DataOutputStream(socket.getOutputStream());
            DataInputStream bufferedInputStream = new DataInputStream(socket.getInputStream());

            // Send device info JSON
            JSONObject deviceInfo = new JSONObject();
            deviceInfo.put("device_type", DEVICE_TYPE);
            deviceInfo.put("os", "Android");
            byte[] sendData = deviceInfo.toString().getBytes(StandardCharsets.UTF_8);

            // Send size as little-endian
            ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
            sizeBuffer.putLong(sendData.length);
            bufferedOutputStream.write(sizeBuffer.array());
            bufferedOutputStream.flush();

            // Send JSON data
            bufferedOutputStream.write(sendData);
            bufferedOutputStream.flush();
            FileLogger.log("WaitingToReceive", "Sent JSON data");

            // Read response size
            byte[] recvSizeBuf = new byte[Long.BYTES];
            int read = bufferedInputStream.read(recvSizeBuf);
            if (read == -1) {
                throw new IOException("Connection closed while reading size");
            }

            long jsonSize = ByteBuffer.wrap(recvSizeBuf).order(ByteOrder.LITTLE_ENDIAN).getLong();

            // Read JSON data
            byte[] recvBuf = new byte[(int) jsonSize];
            int totalBytesRead = 0;
            while (totalBytesRead < jsonSize) {
                int bytesRead = bufferedInputStream.read(recvBuf, totalBytesRead, recvBuf.length - totalBytesRead);
                if (bytesRead == -1) {
                    throw new IOException("Connection closed while reading data");
                }
                totalBytesRead += bytesRead;
            }

            String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
            JSONObject receivedJson = new JSONObject(jsonStr);
            FileLogger.log("WaitingToReceive", "Received JSON: " + receivedJson);

            // Close connections before starting new activity
            socket.close();
            serverSocket.close();

            // Launch appropriate activity
            if (receivedJson.getString("device_type").equals("python")) {
                Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivityPython.class);
                intent.putExtra("receivedJson", receivedJson.toString());
                startActivity(intent);
            } else if (receivedJson.getString("device_type").equals("java")) {
                Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
                intent.putExtra("receivedJson", receivedJson.toString());
                startActivity(intent);
            }

        } catch (Exception e) {
            FileLogger.log("WaitingToReceive", "TCP connection error", e);
        } finally {
            try {
                if (socket != null) socket.close();
                if (serverSocket != null) serverSocket.close();
            } catch (IOException e) {
                FileLogger.log("WaitingToReceive", "Error closing sockets", e);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeAllSockets();
    }

}