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
    private static final int SENDER_PORT_JSON = 53000; // Response port for JSON on the Python app
    private static final int RECEIVER_PORT_JSON = 54000; // TCP port for Python app communication
    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices
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
        BufferedOutputStream outputStream = null;
        BufferedInputStream inputStream = null;
        FileLogger.log("WaitingToReceive", "Establishing TCP connection with Sender");

        try {
            serverSocket = new ServerSocket(RECEIVER_PORT_JSON);
            FileLogger.log("WaitingToReceive", "Waiting for incoming connections on port " + RECEIVER_PORT_JSON);

            while (true) {
                FileLogger.log("WaitingToReceive", "Waiting for incoming connections...");
                socket = serverSocket.accept();
                FileLogger.log("WaitingToReceive", "Accepted connection from: " + socket.getInetAddress().toString());

                DataOutputStream bufferedOutputStream = new DataOutputStream(socket.getOutputStream());
                DataInputStream bufferedInputStream = new DataInputStream(socket.getInputStream());

                // Send JSON data first
                JSONObject deviceInfo = new JSONObject();
                deviceInfo.put("device_type", DEVICE_TYPE);
                deviceInfo.put("os", "Android");
                String deviceInfoStr = deviceInfo.toString();
                byte[] sendData = deviceInfoStr.getBytes(StandardCharsets.UTF_8);
                FileLogger.log("WaitingToReceive", "Encoded JSON data size: " + sendData.length);

                // Convert the JSON size to little-endian bytes and send it first
                ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                sizeBuffer.putLong(sendData.length);
                bufferedOutputStream.write(sizeBuffer.array());
                bufferedOutputStream.flush();

                // Send the actual JSON data encoded in UTF-8
                bufferedOutputStream.write(sendData);
                bufferedOutputStream.flush();

                FileLogger.log("WaitingToReceive", "Sent JSON data to receiver");

                Socket finalSocket = socket;

                // Flag for handling which activity to launch
                final JSONObject[] receivedJsonContainer = new JSONObject[1]; // Use array to allow modification inside thread

                Thread receiveThread = new Thread(() -> {
                    try {
                        // Read the JSON size first (as a long, little-endian)
                        byte[] recvSizeBuf = new byte[Long.BYTES];
                        if (bufferedInputStream.read(recvSizeBuf) == -1) {
                            FileLogger.log("WaitingToReceive", "End of stream reached while reading size");
                            return;
                        }

                        ByteBuffer sizeBufferReceived = ByteBuffer.wrap(recvSizeBuf).order(ByteOrder.LITTLE_ENDIAN);
                        long jsonSize = sizeBufferReceived.getLong();

                        // Read the actual JSON data
                        byte[] recvBuf = new byte[(int) jsonSize];
                        int totalBytesRead = 0;

                        while (totalBytesRead < recvBuf.length) {
                            int bytesRead = bufferedInputStream.read(recvBuf, totalBytesRead, recvBuf.length - totalBytesRead);
                            if (bytesRead == -1) {
                                FileLogger.log("WaitingToReceive", "End of stream reached before reading complete data");
                                return;
                            }
                            totalBytesRead += bytesRead;
                        }

                        // Convert the received bytes into a JSON string
                        String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
                        JSONObject receivedJson = new JSONObject(jsonStr);
                        FileLogger.log("WaitingToReceive", "Received JSON data: " + receivedJson.toString());
                        receivedJsonContainer[0] = receivedJson;

                    } catch (Exception e) {
                        FileLogger.log("WaitingToReceive", "Error receiving JSON data", e);
                    } finally {
                        try {
                            if (bufferedInputStream != null) bufferedInputStream.close();
                            if (bufferedOutputStream != null) bufferedOutputStream.close();
                            if (finalSocket != null && !finalSocket.isClosed()) finalSocket.close();
                        } catch (IOException e) {
                            FileLogger.log("WaitingToReceive", "Error closing socket resources", e);
                        }
                    }
                });
                // Start the receiving thread and wait for it to complete
                receiveThread.start();
                receiveThread.join(); // Wait until the thread finishes before continuing

                // Once JSON is received, decide which activity to start based on the device_type
                JSONObject receivedJson = receivedJsonContainer[0];
                if (receivedJson != null) {
                    // Close socket and serverSocket before starting the new activity
                    if (serverSocket != null && !serverSocket.isClosed()) serverSocket.close();
                    if (socket != null && !socket.isClosed()) socket.close();
                    if (receivedJson.getString("device_type").equals("python")) {
                        FileLogger.log("WaitingToReceive", "Received JSON data from Python app");

                        // Close sockets
                        closeAllSockets();

                        // Start the new activity
                        Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivityPython.class);
                        intent.putExtra("receivedJson", receivedJson.toString());
                        startActivity(intent);

                    } else if (receivedJson.getString("device_type").equals("java")) {
                        FileLogger.log("WaitingToReceive", "Received JSON data from Java app");

                        // Close sockets
                        closeAllSockets();

                        // Start the new activity
                        Intent intent = new Intent(WaitingToReceiveActivity.this, ReceiveFileActivity.class);
                        intent.putExtra("receivedJson", receivedJson.toString());
                        startActivity(intent);

                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("WaitingToReceive", "Error establishing TCP connection", e);
        } finally {
            // Make sure the serverSocket is only closed once we're done with all transactions
            try {
                if (serverSocket != null && !serverSocket.isClosed()) serverSocket.close();
                FileLogger.log("WaitingToReceive", "ServerSocket closed");
            } catch (IOException e) {
                FileLogger.log("WaitingToReceive", "Error closing ServerSocket", e);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeAllSockets();
    }

}