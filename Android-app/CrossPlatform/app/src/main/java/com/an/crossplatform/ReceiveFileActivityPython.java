package com.an.crossplatform;

import android.os.AsyncTask;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONObject;

import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;

public class ReceiveFileActivityPython extends AppCompatActivity {

    private String senderJson;
    private String deviceName;
    private String osType;
    private String senderIp;

    // Server socket to accept connections
    private ServerSocket serverSocket;
    private Socket clientSocket;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        // Retrieve senderJson from the intent
        senderJson = getIntent().getStringExtra("receivedJson");
        Log.d("ReceiveFileActivityPython", "Received JSON: " + senderJson);

        senderIp = getIntent().getStringExtra("senderIp");

        // Parse the JSON and extract device info
        try {
            osType = new JSONObject(senderJson).getString("os");
            deviceName = new JSONObject(senderJson).getString("device_name");
        } catch (Exception e) {
            Log.e("ReceiveFileActivityPython", "Failed to retrieve OS type", e);
        }

        Log.d("ReceiveFileActivityPython", "OS Type: " + osType);

        // Update the TextView with the message
        TextView txt_waiting = findViewById(R.id.txt_waiting);
        txt_waiting.setText("Waiting to receive file from " + deviceName);

        // Start the connection task as soon as the activity starts
        new ConnectionTask().execute();
    }

    // AsyncTask to handle the connection in the background
    private class ConnectionTask extends AsyncTask<Void, Void, Boolean> {

        @Override
        protected Boolean doInBackground(Void... voids) {
            return initializeConnection();
        }

        @Override
        protected void onPostExecute(Boolean connectionSuccessful) {
            if (connectionSuccessful) {
                Log.d("ReceiveFileActivityPython", "Connection established with the sender.");
                // You can update the UI or proceed with further logic here
                TextView txt_waiting = findViewById(R.id.txt_waiting);
                txt_waiting.setText("Connected to " + deviceName + ". Ready to receive files.");
            } else {
                Log.e("ReceiveFileActivityPython", "Failed to establish connection.");
            }
        }

        private boolean initializeConnection() {
            try {
                // Close any existing server socket
                if (serverSocket != null && !serverSocket.isClosed()) {
                    serverSocket.close();
                }

                // Create a new server socket and bind to the specific port
                serverSocket = new ServerSocket(12345); // Replace with the desired port
                Log.d("ReceiveFileActivityPython", "Waiting for a connection...");

                // Wait for a client connection
                clientSocket = serverSocket.accept();
                Log.d("ReceiveFileActivityPython", "Connected to " + clientSocket.getInetAddress().getHostAddress());

                return true;  // Connection successful
            } catch (IOException e) {
                Log.e("ReceiveFileActivityPython", "Error initializing connection", e);
                return false;  // Connection failed
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Clean up the socket when the activity is destroyed
        try {
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
            }
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
        } catch (IOException e) {
            Log.e("ReceiveFileActivityPython", "Error closing sockets", e);
        }
    }
}
