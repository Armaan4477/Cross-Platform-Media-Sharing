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
            try {
                DatagramSocket socket = new DatagramSocket();
                socket.setBroadcast(true);

                byte[] sendData = "DISCOVER".getBytes();
                DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, InetAddress.getByName("255.255.255.255"), UDP_PORT);
                socket.send(sendPacket);

                socket.close();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private void startReceiverThread() {
        new Thread(() -> {
            try {
                DatagramSocket socket = new DatagramSocket(UDP_PORT);
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
            }
        }).start();
    }
}
