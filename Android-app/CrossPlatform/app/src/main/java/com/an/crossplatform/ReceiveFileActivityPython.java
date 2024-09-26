package com.an.crossplatform;

import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

public class ReceiveFileActivityPython extends AppCompatActivity {

    private String senderJson;
    private String deviceType;
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
            deviceType = new JSONObject(senderJson).getString("device_type");
        } catch (Exception e) {
            Log.e("ReceiveFileActivityPython", "Failed to retrieve OS type", e);
        }

        Log.d("ReceiveFileActivityPython", "OS Type: " + osType);

        // Update the TextView with the message
        TextView txt_waiting = findViewById(R.id.txt_waiting);
        txt_waiting.setText("Waiting to receive file from " + deviceType);

        // Start the connection task as soon as the activity starts
        new ConnectionTask().execute();
    }

    // Update your ConnectionTask to receive files in the background
    private class ConnectionTask extends AsyncTask<Void, Void, Boolean> {
        @Override
        protected Boolean doInBackground(Void... voids) {
            boolean connectionSuccessful = initializeConnection();
            if (connectionSuccessful) {
                receiveFiles(); // Call receiveFiles here
            }
            return connectionSuccessful;  // Return the connection status
        }

        @Override
        protected void onPostExecute(Boolean connectionSuccessful) {
            if (connectionSuccessful) {
                Log.d("ReceiveFileActivityPython", "Connection established with the sender.");
                // Update the UI after connection is established
                TextView txt_waiting = findViewById(R.id.txt_waiting);
                txt_waiting.setText("Receiving files from " + deviceType);
            } else {
                Log.e("ReceiveFileActivityPython", "Failed to establish connection.");
            }
        }
    }

    private boolean initializeConnection() {
        try {
            // Close any existing server socket
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }

            // Create a new server socket and bind to the specific port
            serverSocket = new ServerSocket(58000); // Replace with the desired port
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

    private void receiveFiles() {
        Log.d("ReceiveFileActivity", "File reception started.");
        try {
            // Load the save directory from config
            File configFile = new File(getFilesDir(), "config.json");
            String saveToDirectory = loadSaveDirectoryFromConfig(configFile);

            // Convert URI-like path to a proper file path
            String actualPath = saveToDirectory.replace("/tree/primary:", "")
                    .replace("Download", Environment.DIRECTORY_DOWNLOADS)
                    .replace("/", File.separator);
            actualPath = Environment.getExternalStorageDirectory().getPath() + "/" + actualPath; // Ensure proper slash

            // Create the directory if it doesn't exist
            File directory = new File(actualPath);
            if (!directory.exists()) {
                boolean dirCreated = directory.mkdirs();
                if (dirCreated) {
                    Log.d("ReceiveFileActivity", "Created directory: " + actualPath);
                } else {
                    Log.e("ReceiveFileActivity", "Failed to create directory: " + actualPath);
                    return; // Exit if directory creation fails
                }
            }

            while (true) {
                // Receive and decode encryption flag
                byte[] encryptionFlagBytes = new byte[8];
                clientSocket.getInputStream().read(encryptionFlagBytes);
                String encryptionFlag = new String(encryptionFlagBytes).trim();
                Log.d("ReceiveFileActivity", "Received encryption flag: " + encryptionFlag);

                if (encryptionFlag.isEmpty()) {
                    Log.d("ReceiveFileActivity", "End of transfer signal received.");
                    break;
                }

                // Check last character of encryption flag to determine if encryption is enabled
                boolean halt = encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h';
                Log.d("ReceiveFileActivity", "Encryption halt: " + halt);
                if (halt) {
                    Log.e("ReceiveFileActivity", "Encryption halt received. File transfer aborted.");
                    break;
                }

                // Receive file name size
                byte[] fileNameSizeBytes = new byte[8];
                clientSocket.getInputStream().read(fileNameSizeBytes);
                long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();
                Log.d("ReceiveFileActivity", "File name size received: " + fileNameSize);

                // Receive file name
                byte[] fileNameBytes = new byte[(int) fileNameSize];
                clientSocket.getInputStream().read(fileNameBytes);
                String fileName = new String(fileNameBytes, StandardCharsets.UTF_8).replace('\\', '/'); // Use UTF-8 for decoding
                Log.d("ReceiveFileActivity", "Normalized file name: " + fileName);

                // Receive file size
                byte[] fileSizeBytes = new byte[8];
                clientSocket.getInputStream().read(fileSizeBytes);
                long fileSize = ByteBuffer.wrap(fileSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();
                Log.d("ReceiveFileActivity", "Receiving file " + fileName + ", size: " + fileSize + " bytes");

                // Validate file size
                if (fileSize < 0) {
                    Log.e("ReceiveFileActivity", "Received invalid file size: " + fileSize);
                    continue; // Skip this iteration or handle accordingly
                }

                // Receive file data
                File receivedFile = new File(directory, fileName); // Save to the specified directory
                FileOutputStream fos = new FileOutputStream(receivedFile);

                byte[] buffer = new byte[4096];
                long receivedSize = 0;
                while (receivedSize < fileSize) {
                    int bytesRead = clientSocket.getInputStream().read(buffer, 0, (int) Math.min(buffer.length, fileSize - receivedSize));
                    if (bytesRead == -1) {
                        Log.e("ReceiveFileActivity", "Error reading file data. Connection might have been lost.");
                        break; // Handle connection loss or other issues
                    }
                    fos.write(buffer, 0, bytesRead);
                    receivedSize += bytesRead;
                    Log.d("ReceiveFileActivity", "Received " + receivedSize + "/" + fileSize + " bytes");
                }
                fos.close();
                Log.d("ReceiveFileActivity", "File " + fileName + " received successfully.");
            }
        } catch (IOException e) {
            Log.e("ReceiveFileActivity", "Error receiving files", e);
        }
    }

    // Method to load the save directory from config.json
    private String loadSaveDirectoryFromConfig(File configFile) {
        String saveToDirectory = getFilesDir().getPath(); // Default directory if config fails
        try {
            FileInputStream fis = new FileInputStream(configFile);
            BufferedReader reader = new BufferedReader(new InputStreamReader(fis));
            StringBuilder jsonBuilder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                jsonBuilder.append(line);
            }
            reader.close();
            JSONObject config = new JSONObject(jsonBuilder.toString());
            saveToDirectory = config.optString("save_to_directory", saveToDirectory);
        } catch (Exception e) {
            Log.e("ReceiveFileActivity", "Error loading config.json", e);
        }
        return saveToDirectory;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Close sockets on activity destruction
        try {
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
            }
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
        } catch (IOException e) {
            Log.e("ReceiveFileActivity", "Error closing sockets", e);
        }
    }
}