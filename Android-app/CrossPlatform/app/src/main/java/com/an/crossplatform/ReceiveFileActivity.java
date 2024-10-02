package com.an.crossplatform;

import android.annotation.SuppressLint;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.widget.ProgressBar;
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

public class ReceiveFileActivity extends AppCompatActivity {

    private String senderJson;
    private String deviceType;
    private String osType;
    private String senderIp;

    private ServerSocket serverSocket;
    private Socket clientSocket;
    private String destinationFolder;
    private JSONArray metadata;
    private String saveToDirectory;
    private ProgressBar progressBar;
    private TextView txt_waiting;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);
        progressBar = findViewById(R.id.fileProgressBar);
        txt_waiting = findViewById(R.id.txt_waiting);

        senderJson = getIntent().getStringExtra("receivedJson");
        senderIp = getIntent().getStringExtra("senderIp");

        try {
            JSONObject jsonObject = new JSONObject(senderJson);
            osType = jsonObject.getString("os");
            deviceType = jsonObject.getString("device_type");
        } catch (JSONException e) {
            Log.e("ReceiveFileActivity", "Failed to retrieve OS type", e);
        }

        txt_waiting.setText("Waiting to receive file from " + deviceType);

        new ConnectionTask().execute();
    }

    private class ConnectionTask extends AsyncTask<Void, Void, Boolean> {
        @Override
        protected Boolean doInBackground(Void... voids) {
            return initializeConnection();
        }

        @Override
        protected void onPostExecute(Boolean connectionSuccessful) {
            if (connectionSuccessful) {
                Log.d("ReceiveFileActivity", "Connection established with the sender.");
                txt_waiting.setText("Receiving files from " + deviceType);
                new ReceiveFilesTask().execute();
            } else {
                Log.e("ReceiveFileActivity", "Failed to establish connection.");
            }
        }
    }

    private boolean initializeConnection() {
        try {
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            serverSocket = new ServerSocket(58100);
            Log.d("ReceiveFileActivity", "Waiting for a connection...");
            clientSocket = serverSocket.accept();
            Log.d("ReceiveFileActivity", "Connected to " + clientSocket.getInetAddress().getHostAddress());
            return true;
        } catch (IOException e) {
            Log.e("ReceiveFileActivity", "Error initializing connection", e);
            return false;
        }
    }

    @SuppressLint("StaticFieldLeak")
    private class ReceiveFilesTask extends AsyncTask<Void, Integer, Void> {
        @Override
        protected Void doInBackground(Void... voids) {
            receiveFiles();
            return null;
        }

        @Override
        protected void onProgressUpdate(Integer... values) {
            progressBar.setProgress(values[0]);
        }

        @Override
        protected void onPostExecute(Void result) {
            txt_waiting.setText("File transfer completed");
            progressBar.setProgress(0);
        }

        private void receiveFiles() {
            Log.d("ReceiveFileActivity", "File reception started.");
            try {
                File configFile = new File(getFilesDir(), "config/config.json");
                saveToDirectory = loadSaveDirectoryFromConfig(configFile);

                String actualPath = saveToDirectory.replace("/tree/primary:", "")
                        .replace("Download", Environment.DIRECTORY_DOWNLOADS)
                        .replace("/", File.separator);
                actualPath = Environment.getExternalStorageDirectory().getPath() + File.separator + actualPath;

                File directory = new File(actualPath);
                if (!directory.exists() && !directory.mkdirs()) {
                    Log.e("ReceiveFileActivity", "Failed to create directory: " + actualPath);
                    return;
                }

                destinationFolder = actualPath;
                JSONArray metadataArray = null;

                while (true) {
                    byte[] encryptionFlagBytes = new byte[8];
                    clientSocket.getInputStream().read(encryptionFlagBytes);
                    String encryptionFlag = new String(encryptionFlagBytes).trim();

                    if (encryptionFlag.isEmpty() || encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {
                        break;
                    }

                    byte[] fileNameSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileNameSizeBytes);
                    long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileNameSize == 0) {
                        break;
                    }

                    byte[] fileNameBytes = new byte[(int) fileNameSize];
                    clientSocket.getInputStream().read(fileNameBytes);
                    String fileName = new String(fileNameBytes, StandardCharsets.UTF_8).replace('\\', '/');

                    byte[] fileSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileSizeBytes);
                    long fileSize = ByteBuffer.wrap(fileSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileSize < 0) {
                        continue;
                    }

                    if (fileName.equals("metadata.json")) {
                        metadataArray = receiveMetadata(fileSize);
                        if (metadataArray != null) {
                            destinationFolder = createFolderStructure(metadataArray, actualPath);
                        }
                        continue;
                    }

                    String filePath = (metadataArray != null) ? getFilePathFromMetadata(metadataArray, fileName) : fileName;
                    File receivedFile = new File(destinationFolder, filePath);

                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists() && !parentDir.mkdirs()) {
                        Log.e("ReceiveFileActivity", "Failed to create directory: " + parentDir.getPath());
                        continue;
                    }

                    try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
                        byte[] buffer = new byte[8192]; // Increased buffer size for faster transfer
                        long receivedSize = 0;
                        while (receivedSize < fileSize) {
                            int bytesRead = clientSocket.getInputStream().read(buffer, 0, (int) Math.min(buffer.length, fileSize - receivedSize));
                            if (bytesRead == -1) {
                                break;
                            }
                            fos.write(buffer, 0, bytesRead);
                            receivedSize += bytesRead;

                            // Update progress
                            int progress = (int) ((receivedSize * 100) / fileSize);
                            publishProgress(progress);
                        }
                    }
                }
            } catch (IOException e) {
                Log.e("ReceiveFileActivity", "Error receiving files", e);
            }
        }
    }

    private String getFilePathFromMetadata(JSONArray metadataArray, String fileName) {
        for (int i = 0; i < metadataArray.length(); i++) {
            try {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String path = fileInfo.optString("path", "");
                if (path.endsWith(fileName)) {
                    return path;
                }
            } catch (JSONException e) {
                Log.e("ReceiveFileActivity", "Error processing metadata for file: " + fileName, e);
            }
        }
        return fileName; // Return original fileName if not found in metadata
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
            // Check if the base_folder_name has the word primary in it
            if(lastMetadata.optString("base_folder_name", "").contains("primary")) {
                topLevelFolder = lastMetadata.optString("base_folder_name", "").replace("primary%3A", "");
            } else {
                topLevelFolder = lastMetadata.optString("base_folder_name", "");
            }
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