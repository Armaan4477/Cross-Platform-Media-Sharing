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
    private String destinationFolder; // Declare destinationFolder here
    private JSONArray metadata; // Assuming metadata is also stored at class level
    private String saveToDirectory;

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
            serverSocket = new ServerSocket(58100); // Replace with the desired port
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

            // Create the main directory if it doesn't exist
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
                    Log.d("ReceiveFileActivity", "Dropped redundant data: " + encryptionFlag);
                    break;
                }

                if (encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {
                    Log.e("ReceiveFileActivity", "Received halt signal. Stopping file reception.");
                    break; // Halting signal
                }

                // Receive file name size
                byte[] fileNameSizeBytes = new byte[8];
                clientSocket.getInputStream().read(fileNameSizeBytes);
                long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();
                Log.d("ReceiveFileActivity", "File name size received: " + fileNameSize);

                // End of transfer signal
                if (fileNameSize == 0) {
                    Log.d("ReceiveFileActivity", "End of transfer signal received.");
                    break;
                }

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

                // Check if it's metadata
                if (fileName.equals("metadata.json")) {
                    Log.d("ReceiveFileActivity", "Receiving metadata file.");
                    JSONArray metadataArray = receiveMetadata(fileSize); // Assuming this returns a JSONArray

                    if (metadataArray != null && metadataArray.length() > 0) {
                        this.metadata = metadataArray; // Store the received metadata

                        try {
                            // Access the last element
                            JSONObject lastMetadata = metadataArray.getJSONObject(metadataArray.length() - 1);

                            // Check if it has the base folder name
                            if (lastMetadata.has("base_folder_name")) {
                                String baseFolderName = lastMetadata.getString("base_folder_name");
                                if (!baseFolderName.isEmpty()) {
                                    this.destinationFolder = createFolderStructure(metadataArray, directory.getPath()); // Pass the directory path
                                } else {
                                    this.destinationFolder = directory.getPath(); // Set to default
                                }
                            } else {
                                this.destinationFolder = directory.getPath(); // Set to default
                            }
                            Log.d("ReceiveFileActivity", "Metadata processed. Destination folder set to: " + this.destinationFolder);
                        } catch (JSONException e) {
                            Log.e("ReceiveFileActivity", "Error processing metadata JSON", e);
                        }
                    } else {
                        Log.e("ReceiveFileActivity", "No valid metadata received.");
                    }
                } else {
                    // Normal file reception logic
                    File receivedFile = new File(destinationFolder, fileName); // Save to the specified destination folder

                    // Ensure the parent directory exists before creating the file
                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists()) {
                        boolean dirCreated = parentDir.mkdirs(); // Create the parent directory
                        if (dirCreated) {
                            Log.d("ReceiveFileActivity", "Created directory: " + parentDir.getPath());
                        } else {
                            Log.e("ReceiveFileActivity", "Failed to create directory: " + parentDir.getPath());
                            continue; // Skip this file if the directory cannot be created
                        }
                    }

                    // Handle file writing
                    try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
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
                        Log.d("ReceiveFileActivity", "File " + fileName + " received successfully.");
                    } catch (IOException e) {
                        Log.e("ReceiveFileActivity", "Error writing file " + fileName, e);
                    }
                }
            }
        } catch (IOException e) {
            Log.e("ReceiveFileActivity", "Error receiving files", e);
        }
    }

    // Method to load the save directory from config.json
    private String loadSaveDirectoryFromConfig(File configFile) {
        String saveToDirectory = getFilesDir().getPath(); // Default directory if config fails
        try {
            // Update the path to point to the correct location of config.json
            configFile = new File(getFilesDir(), "config/config.json"); // Corrected path

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

    private JSONArray receiveMetadata(long fileSize) {
        byte[] receivedData = new byte[(int) fileSize];
        try {
            clientSocket.getInputStream().read(receivedData);
            String metadataJson = new String(receivedData, StandardCharsets.UTF_8);
            return new JSONArray(metadataJson); // Change to JSONArray
        } catch (IOException e) {
            Log.e("ReceiveFileActivity", "Error receiving metadata", e);
        } catch (JSONException e) {
            Log.e("ReceiveFileActivity", "Error parsing metadata JSON", e);
        }
        return null; // Return null or handle accordingly if metadata reception fails
    }

    private String createFolderStructure(JSONArray metadataArray, String defaultDir) {
        if (metadataArray.length() == 0) {
            Log.e("ReceiveFileActivity", "No metadata provided for folder structure.");
            return defaultDir; // Return default if no metadata
        }

        String topLevelFolder = ""; // Variable to hold the top-level folder name

        try {
            // Extract the base folder name from the last entry
            JSONObject lastMetadata = metadataArray.getJSONObject(metadataArray.length() - 1);
            topLevelFolder = lastMetadata.optString("base_folder_name", "");

            if (topLevelFolder.isEmpty()) {
                Log.e("ReceiveFileActivity", "Base folder name not found in metadata");
                return defaultDir; // Return default if no base folder
            }

        } catch (JSONException e) {
            Log.e("ReceiveFileActivity", "Error processing metadata JSON to extract base folder name", e);
            return defaultDir; // Return default if any error occurs
        }

        // Construct the destination folder path
        String destinationFolder = new File(defaultDir, topLevelFolder).getPath();
        Log.d("ReceiveFileActivity", "Destination folder: " + destinationFolder);

        File destinationDir = new File(destinationFolder);
        if (!destinationDir.exists()) {
            destinationDir.mkdirs(); // Create the base folder if it doesn't exist
            Log.d("ReceiveFileActivity", "Created base folder: " + destinationFolder);
        }

        // Process each file info in the metadata array
        for (int i = 0; i < metadataArray.length() - 1; i++) { // Exclude the last entry
            try {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String filePath = fileInfo.optString("path", "");
                if (filePath.equals(".delete")) {
                    continue; // Skip paths marked for deletion
                }

                File folderPath = new File(destinationFolder, filePath).getParentFile();
                if (folderPath != null && !folderPath.exists()) {
                    folderPath.mkdirs(); // Create the folder structure if it doesn't exist
                    Log.d("ReceiveFileActivity", "Created folder: " + folderPath.getPath());
                }
            } catch (JSONException e) {
                Log.e("ReceiveFileActivity", "Error processing file info in metadata", e);
                // Continue to the next file if there's an error with the current one
            }
        }

        return destinationFolder; // Return the path of the created folder structure
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