package com.an.crossplatform;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import org.json.JSONObject;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.atomic.AtomicBoolean;

public class DiscoverDevicesActivity extends AppCompatActivity {

    private static final int DISCOVER_PORT = 12345; // Port for sending DISCOVER messages
    private static final int RESPONSE_PORT = 12346; // Port for receiving responses
    private Button btnDiscover, btnConnect;
    private ListView listDevices;
    private ArrayList<String> devices = new ArrayList<>();
    private ArrayAdapter<String> adapter;
    private DatagramSocket discoverSocket;
    private DatagramSocket responseSocket;
    private AtomicBoolean isDiscovering = new AtomicBoolean(false);
    private String selectedDeviceIP;
    private String selectedDeviceName;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_discover_devices);

        btnDiscover = findViewById(R.id.btn_discover);
        btnConnect = findViewById(R.id.btn_connect);
        listDevices = findViewById(R.id.list_devices);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, devices);
        listDevices.setAdapter(adapter);

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
                System.out.println("Selected device IP: " + selectedDeviceIP);
                exchangeJsonAndStartSendFileActivity();
            }
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
        isDiscovering.set(true); // Set the flag to true
        new Thread(() -> {
            try {
                discoverSocket = new DatagramSocket();
                discoverSocket.setBroadcast(true);

                byte[] sendData = "DISCOVER".getBytes();
                InetAddress broadcastAddress = InetAddress.getByName("255.255.255.255");
                DatagramPacket sendPacket = new DatagramPacket(sendData, sendData.length, broadcastAddress, DISCOVER_PORT);
                Log.d("DiscoverDevices", "Sending DISCOVER message to broadcast address " + broadcastAddress.getHostAddress() + " on port " + DISCOVER_PORT);

                for (int i = 0; i < 120 && isDiscovering.get(); i++) { // 120 iterations for 2 minutes
                    discoverSocket.send(sendPacket);
                    Log.d("DiscoverDevices", "Sent DISCOVER message iteration: " + (i + 1));
                    Thread.sleep(1000);
                }

            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                if (discoverSocket != null && !discoverSocket.isClosed()) {
                    discoverSocket.close(); // Ensure socket is closed when done
                }
            }
        }).start();
    }

    private void startReceiverThread() {
        new Thread(() -> {
            try {
                responseSocket = new DatagramSocket(RESPONSE_PORT); // Bind to port 12346
                Log.d("DiscoverDevices", "Listening for RECEIVER messages on port " + RESPONSE_PORT);

                byte[] recvBuf = new byte[15000];

                while (isDiscovering.get()) {
                    DatagramPacket receivePacket = new DatagramPacket(recvBuf, recvBuf.length);
                    responseSocket.receive(receivePacket);

                    String message = new String(receivePacket.getData(), 0, receivePacket.getLength()).trim();
                    Log.d("DiscoverDevices", "Received raw message: " + message);
                    Log.d("DiscoverDevices", "Message length: " + receivePacket.getLength());
                    Log.d("DiscoverDevices", "Sender address: " + receivePacket.getAddress().getHostAddress());
                    Log.d("DiscoverDevices", "Sender port: " + receivePacket.getPort());

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
                        Log.d("DiscoverDevices", "Unexpected message: " + message);
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
            try {
                // Establish a socket connection to the selected device IP on the RESPONSE_PORT
                Socket socket = new Socket(selectedDeviceIP, RESPONSE_PORT);

                DataOutputStream dos = new DataOutputStream(socket.getOutputStream());
                DataInputStream dis = new DataInputStream(socket.getInputStream());

                // Create a JSON object containing the device information
                JSONObject jsonObject = new JSONObject();
                jsonObject.put("device_type", "java"); // Or "android" as per your requirement
                jsonObject.put("os", "Android");

                // Convert the JSON object to a UTF-8 encoded byte array
                String jsonString = jsonObject.toString();
                byte[] jsonBytes = jsonString.getBytes(StandardCharsets.UTF_8);

                // Send the length of the JSON byte array followed by the JSON data itself
                dos.writeInt(jsonBytes.length); // Writing the length of the byte array
                dos.write(jsonBytes); // Writing the actual JSON byte array
                dos.flush();

                // Receive the JSON data from the receiver
                int jsonLength = dis.readInt();
                byte[] receivedJsonBytes = new byte[jsonLength];
                dis.readFully(receivedJsonBytes);
                String receivedJsonString = new String(receivedJsonBytes, StandardCharsets.UTF_8);
                Log.d("DiscoverDevices", "Received JSON data: " + receivedJsonString);
                Log.d("DiscoverDevices", "Sent JSON data: " + jsonString);

                // Close the socket after sending the data
                socket.close();

                // Start SendFileActivity and pass the encoded JSON string
                Intent intent = new Intent(DiscoverDevicesActivity.this, SendFileActivity.class);
                intent.putExtra("receiverJson", jsonString); // You can also pass the original JSON string
                startActivity(intent);
                finish();

            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }


    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopDiscovering();
    }
}
