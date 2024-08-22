package com.an.crossplatform;

import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import androidx.appcompat.app.AppCompatActivity;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.ArrayList;

public class DiscoverDevicesActivity extends AppCompatActivity {

    private static final int UDP_PORT = 12345;
    private Button btnDiscover;
    private ListView listDevices;
    private ArrayList<String> devices = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private DatagramSocket socket;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_discover_devices);

        btnDiscover = findViewById(R.id.btn_discover);
        listDevices = findViewById(R.id.list_devices);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, devices);
        listDevices.setAdapter(adapter);

        btnDiscover.setOnClickListener(v -> {
            discoverDevices();
            startReceiverThread();
        });
    }

    private void discoverDevices() {
        new Thread(() -> {
            DatagramSocket socket = null;
            try {
                socket = new DatagramSocket();
                socket.setBroadcast(true);

                byte[] sendData = "DISCOVER".getBytes();
                DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, InetAddress.getByName("255.255.255.255"), UDP_PORT);
                socket.send(sendPacket);

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
                // Close any existing socket bound to the port
                if (this.socket != null && !this.socket.isClosed()) {
                    this.socket.close();
                }

                socket = new DatagramSocket(UDP_PORT);
                this.socket = socket; // Store the socket reference for future use

                byte[] recvBuf = new byte[15000];

                while (true) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    socket.receive(receivePacket);

                    String message = new String(receivePacket.getData()).trim();
                    if (message.startsWith("RECEIVE")) {
                        String deviceIP = receivePacket.getAddress().getHostAddress();
                        String deviceName = message.substring(7);

                        runOnUiThread(() -> {
                            devices.add(deviceIP + " - " + deviceName);
                            adapter.notifyDataSetChanged();
                        });
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
        if (socket != null && !socket.isClosed()) {
            socket.close();
        }
    }
}
