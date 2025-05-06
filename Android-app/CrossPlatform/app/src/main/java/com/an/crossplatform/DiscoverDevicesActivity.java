package com.an.crossplatform;

import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.atomic.AtomicBoolean;
import android.content.Context;
import android.net.wifi.WifiManager;
import android.text.format.Formatter;
import androidx.activity.OnBackPressedCallback;

/** @noinspection CallToPrintStackTrace*/
public class DiscoverDevicesActivity extends AppCompatActivity {

    private static final int DISCOVER_PORT = 49185; // Port for sending DISCOVER messages
    private static final int RESPONSE_PORT = 49186; // Port for receiving responses
    private Button btnDiscover, btnConnect;
    private ListView listDevices;
    private ArrayList<String> devices = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private DatagramSocket discoverSocket;
    private DatagramSocket responseSocket;
    private AtomicBoolean isDiscovering = new AtomicBoolean(false);
    private String selectedDeviceIP;
    private String selectedDeviceName;

    private static final int UDP_PORT = 12345; // Discovery port on Android
    private static final int SENDER_PORT_JSON = 53000; // Response port for JSON on Python app
    private static final int RECEIVER_PORT_JSON = 54314; // TCP port for Python app communication
    private String DEVICE_NAME;
    private String DEVICE_TYPE = "java"; // Device type for Android devices
    private int LISTEN_PORT = 12346;
    private Socket tcpSocket;
    private DataOutputStream dataOutputStream;
    private DataInputStream dataInputStream;
    private String broadcastIp = "255.255.255.255";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_discover_devices);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                closeAllSockets();
                forceReleasePort();
                forceReleaseUDPPort();
                new Handler(Looper.getMainLooper()).postDelayed(() -> finish(), 500);
                finish();
            }
        });

        btnDiscover = findViewById(R.id.btn_discover);
        btnConnect = findViewById(R.id.btn_connect);
        listDevices = findViewById(R.id.list_devices);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, devices);
        listDevices.setAdapter(adapter);

        // Call getBroadcastIp when the activity starts
//        String broadcastIp = getBroadcastIp(this);
        FileLogger.log("DiscoverDevices", "BroadcastIP: " + broadcastIp);

        btnDiscover.setOnClickListener(v -> {
            resetSockets();
            discoverDevices();
            startReceiverThread();
        });

        listDevices.setOnItemClickListener((parent, view, position, id) -> {
            stopDiscovering();
            highlightSelectedDevice(view);
            String[] deviceInfo = devices.get(position).split(" - ");
            selectedDeviceIP = deviceInfo[0];
            selectedDeviceName = deviceInfo[1];
            btnConnect.setEnabled(true);
        });

        btnConnect.setOnClickListener(v -> {
            if (selectedDeviceIP != null) {
                btnConnect.setEnabled(false);
                System.out.println("Selected device IP: " + selectedDeviceIP);
                long startTime = System.currentTimeMillis();
//                while (System.currentTimeMillis() - startTime < 15000) {
                    exchangeJsonAndStartSendFileActivity();
//                }
            }
        });
    }

    private void resetSockets() {
        if (discoverSocket != null && !discoverSocket.isClosed()) {
            FileLogger.log("DiscoverDevices", "Closing previous discoverSocket");
            discoverSocket.close();
        }
        if (responseSocket != null && !responseSocket.isClosed()) {
            FileLogger.log("DiscoverDevices", "Closing previous responseSocket");
            responseSocket.close();
        }
    }

    private void discoverDevices() {
        isDiscovering.set(true);
        new Thread(() -> {
            try {
                discoverSocket = new DatagramSocket();
                discoverSocket.setBroadcast(true);

                byte[] sendData = "DISCOVER".getBytes();
                InetAddress broadcastAddress = InetAddress.getByName("255.255.255.255");
                DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, broadcastAddress, DISCOVER_PORT);
                FileLogger.log("DiscoverDevices", "Sending DISCOVER message to broadcast address 255.255.255.255 on port 49185");

                for (int i = 0; i < 120 && isDiscovering.get(); i++) {
                    discoverSocket.send(sendPacket);
                    FileLogger.log("DiscoverDevices", "Sent DISCOVER message iteration: " + (i + 1));
                    Thread.sleep(1000);
                }

            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                if (discoverSocket != null && !discoverSocket.isClosed()) {
                    discoverSocket.close();
                }
            }
        }).start();
    }

    private void closeAllSockets() {
        try {
            // Stop discovery first
            stopDiscovering();

            // Close TCP related resources
            if (dataOutputStream != null) {
                dataOutputStream.close();
                FileLogger.log("DiscoverDevices", "DataOutputStream closed");
            }
            if (dataInputStream != null) {
                dataInputStream.close();
                FileLogger.log("DiscoverDevices", "DataInputStream closed");
            }
            if (tcpSocket != null && !tcpSocket.isClosed()) {
                tcpSocket.close();
                FileLogger.log("DiscoverDevices", "TCP Socket closed");
            }

            // Close UDP sockets
            if (discoverSocket != null && !discoverSocket.isClosed()) {
                discoverSocket.close();
                FileLogger.log("DiscoverDevices", "Discover Socket closed");
            }
            if (responseSocket != null && !responseSocket.isClosed()) {
                responseSocket.close();
                FileLogger.log("DiscoverDevices", "Response Socket closed");
            }

            finish(); // Close the activity
        } catch (IOException e) {
            FileLogger.log("DiscoverDevices", "Error closing sockets", e);
        }
    }

    private void startReceiverThread() {
        new Thread(() -> {
            try {
                responseSocket = new DatagramSocket(RESPONSE_PORT);
                FileLogger.log("DiscoverDevices", "Listening for RECEIVER messages on port " + RESPONSE_PORT);

                byte[] recvBuf = new byte[15000];

                while (isDiscovering.get()) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    responseSocket.receive(receivePacket);

                    String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();
                    FileLogger.log("DiscoverDevices", "Received raw message: " + message);
                    FileLogger.log("DiscoverDevices", "Message length: " + receivePacket.getLength());
                    FileLogger.log("DiscoverDevices", "Sender address: " + receivePacket.getAddress().getHostAddress());
                    FileLogger.log("DiscoverDevices", "Sender port: " + receivePacket.getPort());

                    if (message.startsWith("RECEIVER")) {
                        String deviceIP = receivePacket.getAddress().getHostAddress();
                        String deviceName = message.substring("RECEIVER:".length());

                        runOnUiThread(() -> {
                            String deviceInfo = deviceIP + " - " + deviceName;
                            if (!devices.contains(deviceInfo)) {
                                devices.add(deviceInfo);
                                adapter.notifyDataSetChanged();
                            }
                        });
                    } else {
                        FileLogger.log("DiscoverDevices", "Unexpected message: " + message);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                if (responseSocket != null && !responseSocket.isClosed()) {
                    responseSocket.close(); // Ensure socket is closed when done
                }
            }
        }).start();
    }

    private void stopDiscovering() {
        isDiscovering.set(false); // Set the flag to false
        resetSockets(); // Close sockets to stop sending and receiving
    }

    private void highlightSelectedDevice(android.view.View view) {
        for (int i = 0; i < listDevices.getChildCount(); i++) {
            listDevices.getChildAt(i).setBackgroundColor(ContextCompat.getColor(this, android.R.color.transparent));
        }
        view.setBackgroundColor(ContextCompat.getColor(this, android.R.color.holo_blue_light));
    }

    private void exchangeJsonAndStartSendFileActivity() {
        new Thread(() -> {
            Socket socket = null;
            try {
                socket = new Socket();
                socket.connect(new InetSocketAddress(selectedDeviceIP, RECEIVER_PORT_JSON), 10000);
                FileLogger.log("DiscoverDevices", "Connected to " + selectedDeviceIP + " on port " + RECEIVER_PORT_JSON);

                // Prepare JSON data to send (Android device info)
                JSONObject deviceInfo = new JSONObject();
                deviceInfo.put("device_type", DEVICE_TYPE);
                deviceInfo.put("os", "Android");
                String deviceInfoStr = deviceInfo.toString();
                byte[] sendData = deviceInfoStr.getBytes(StandardCharsets.UTF_8);
                FileLogger.log("WaitingToReceive", "Encoded JSON data size: " + sendData.length);

                DataOutputStream bufferedOutputStream = new DataOutputStream(socket.getOutputStream());
                DataInputStream bufferedInputStream = new DataInputStream(socket.getInputStream());

                // Send JSON size (little-endian)
                ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                sizeBuffer.putLong(sendData.length);
                bufferedOutputStream.write(sizeBuffer.array());
                bufferedOutputStream.flush();

                // Send JSON data
                bufferedOutputStream.write(sendData);
                bufferedOutputStream.flush();

                // Read response JSON size
                byte[] recvSizeBuf = new byte[Long.BYTES];
                bufferedInputStream.read(recvSizeBuf);
                ByteBuffer sizeBufferReceived = ByteBuffer.wrap(recvSizeBuf).order(ByteOrder.LITTLE_ENDIAN);
                long jsonSize = sizeBufferReceived.getLong();

                // Read response JSON data
                byte[] recvBuf = new byte[(int) jsonSize];
                int totalBytesRead = 0;
                while (totalBytesRead < recvBuf.length) {
                    int bytesRead = bufferedInputStream.read(recvBuf, totalBytesRead, recvBuf.length - totalBytesRead);
                    if (bytesRead == -1) {
                        throw new IOException("End of stream reached before reading complete data");
                    }
                    totalBytesRead += bytesRead;
                }

                // Process received JSON
                String jsonStr = new String(recvBuf, StandardCharsets.UTF_8);
                JSONObject receivedJson = new JSONObject(jsonStr);
                FileLogger.log("WaitingToReceive", "Received JSON data: " + receivedJson.toString());

                // Start appropriate activity based on device type
                if (receivedJson.getString("device_type").equals("python")) {
                    Intent intent = new Intent(DiscoverDevicesActivity.this, SendFileActivityPython.class);
                    intent.putExtra("receivedJson", receivedJson.toString());
                    intent.putExtra("selectedDeviceIP", selectedDeviceIP);
                    startActivity(intent);
                    closeAllSockets();
                    finish();
                } else if (receivedJson.getString("device_type").equals("java")) {
                    Intent intent = new Intent(DiscoverDevicesActivity.this, SendFileActivity.class);
                    intent.putExtra("receivedJson", receivedJson.toString());
                    intent.putExtra("selectedDeviceIP", selectedDeviceIP);
                    startActivity(intent);
                    closeAllSockets();
                    finish();
                }

            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                try {
                    if (socket != null) socket.close();
                } catch (Exception ignored) {}
            }
        }).start();
    }

    private void forceReleasePort() {
        int port1 =RECEIVER_PORT_JSON;
        int port2=57341;
        int port3=63152;
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port1);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port1);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port1, e);
        }
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port2);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port2);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port2, e);
        }
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port3);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port3);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port3, e);
        }
    }

    private void forceReleaseUDPPort() {
        int port1=49185;
        int port2=49186;
        try {
            // Find and kill process using the UDP port
            Process process = Runtime.getRuntime().exec("lsof -i udp:" + port1);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (!line.startsWith("COMMAND")) {
                    String[] parts = line.trim().split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("DiscoverDevices", "Killed process " + pid + " using UDP port " + port1);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("DiscoverDevices", "Error releasing UDP port: " + port1, e);
        }

        try {
            // Find and kill process using the UDP port
            Process process = Runtime.getRuntime().exec("lsof -i udp:" + port2);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (!line.startsWith("COMMAND")) {
                    String[] parts = line.trim().split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("DiscoverDevices", "Killed process " + pid + " using UDP port " + port2);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("DiscoverDevices", "Error releasing UDP port: " + port2, e);
        }
    }


    @Override
    protected void onDestroy() {
        closeAllSockets();
        super.onDestroy();
    }
}
