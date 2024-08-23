package com.an.crossplatform;

import android.os.Bundle;
import android.util.Log;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import androidx.appcompat.app.AppCompatActivity;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.ArrayList;

public class DiscoverDevicesActivity extends AppCompatActivity {

    private static final int DISCOVER_PORT = 12345; // Port for sending DISCOVER messages
    private static final int RESPONSE_PORT = 12346; // Port for receiving responses
    private Button btnDiscover;
    private ListView listDevices;
    private ArrayList<String> devices = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private DatagramSocket discoverSocket;
    private DatagramSocket responseSocket;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_discover_devices);

        btnDiscover = findViewById(R.id.btn_discover);
        listDevices = findViewById(R.id.list_devices);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, devices);
        listDevices.setAdapter(adapter);

        btnDiscover.setOnClickListener(v -> {
            resetSockets();
            discoverDevices();
            startReceiverThread();
        });
    }

    private void resetSockets() {
        if (discoverSocket != null && !discoverSocket.isClosed()) {
            Log.d("DiscoverDevices", "Closing previous discoverSocket");
            discoverSocket.close();
        }
        if (responseSocket != null && !responseSocket.isClosed()) {
            Log.d("DiscoverDevices", "Closing previous responseSocket");
            responseSocket.close();
        }
    }

    private void discoverDevices() {
        new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket();
                socket.setBroadcast(true);

                byte[] sendData = "DISCOVER".getBytes();
                InetAddress broadcastAddress = InetAddress.getByName("255.255.255.255");
                DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, broadcastAddress, DISCOVER_PORT);
                Log.d("DiscoverDevices", "Sending DISCOVER message to broadcast address " + broadcastAddress.getHostAddress() + " on port " + DISCOVER_PORT);

                for (int i = 0; i < 120; i++) { // 120 iterations for 2 minutes
                    socket.send(sendPacket);
                    Log.d("DiscoverDevices", "Sent DISCOVER message iteration: " + (i + 1));
                    Thread.sleep(1000);
                }

            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                if (socket != null && !socket.isClosed()) {
                    socket.close();
                }
            }
        }).start();
    }

    private void startReceiverThread() {
        new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket(RESPONSE_PORT); // Bind to port 12346
                Log.d("DiscoverDevices", "Listening for RECEIVER messages on port " + RESPONSE_PORT);

                byte[] recvBuf = new byte[15000];

                while (true) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    socket.receive(receivePacket);

                    String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();
                    Log.d("DiscoverDevices", "Received raw message: " + message);
                    Log.d("DiscoverDevices", "Message length: " + receivePacket.getLength());
                    Log.d("DiscoverDevices", "Sender address: " + receivePacket.getAddress().getHostAddress());
                    Log.d("DiscoverDevices", "Sender port: " + receivePacket.getPort());

                    if (message.startsWith("RECEIVER")) {
                        String deviceIP = receivePacket.getAddress().getHostAddress();
                        String deviceName = message.substring("RECEIVER:".length());

                        runOnUiThread(() -> {
                            devices.add(deviceIP + " - " + deviceName);
                            adapter.notifyDataSetChanged();
                        });
                    } else {
                        Log.d("DiscoverDevices", "Unexpected message: " + message);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                if (socket != null && !socket.isClosed()) {
                    socket.close();
                }
            }
        }).start();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        resetSockets();
    }
}
