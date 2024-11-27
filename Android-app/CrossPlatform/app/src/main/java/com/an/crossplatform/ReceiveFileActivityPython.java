package com.an.crossplatform;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import com.airbnb.lottie.LottieAnimationView;

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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class ReceiveFileActivityPython extends AppCompatActivity {

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
    private LottieAnimationView animationView;
    private LottieAnimationView waitingAnimation;
    private Button openFolder;
    private TextView txt_path;
    private ExecutorService executorService = Executors.newFixedThreadPool(2); // Using 2 threads: one for connection, one for file reception

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);
        progressBar = findViewById(R.id.fileProgressBar);
        txt_waiting = findViewById(R.id.txt_waiting);
        animationView = findViewById(R.id.transfer_animation);
        waitingAnimation = findViewById(R.id.waiting_animation);
        openFolder = findViewById(R.id.openFolder);
        txt_path = findViewById(R.id.path);

        senderJson = getIntent().getStringExtra("receivedJson");
        senderIp = getIntent().getStringExtra("senderIp");

        try {
            JSONObject jsonObject = new JSONObject(senderJson);
            osType = jsonObject.getString("os");
            deviceType = jsonObject.getString("device_type");
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivityPython", "Failed to retrieve OS type", e);
        }

        if(osType.equals("Windows")) {
            txt_waiting.setText("Waiting to Receive files from Windows");
        } else if (osType.equals("Linux")) {
            txt_waiting.setText("Waiting to Receive files from Linux");
        } else if (osType.equals("Darwin")) {
            txt_waiting.setText("Waiting to Receive files from Mac");
        } else {
            txt_waiting.setText("Waiting to Receive files from Python");
        }
        startConnectionTask();
    }

    private class ConnectionTask implements Runnable {
        @Override
        public void run() {
            boolean connectionSuccessful = initializeConnection();
            runOnUiThread(() -> {
                if (connectionSuccessful) {
                    FileLogger.log("ReceiveFileActivityPython", "Connection established with the sender.");
                    if(osType.equals("Windows")) {
                        txt_waiting.setText("Receiving files from Windows");
                    } else if (osType.equals("Linux")) {
                        txt_waiting.setText("Receiving files from Linux");
                    } else if (osType.equals("Darwin")) {
                        txt_waiting.setText("Receiving files from Mac");
                    } else {
                        txt_waiting.setText("Receiving files from Python");
                    }
                    executorService.submit(new ReceiveFilesTask()); // Submit ReceiveFilesTask to executorService
                } else {
                    FileLogger.log("ReceiveFileActivityPython", "Failed to establish connection.");
                }
            });
        }
    }

    private boolean initializeConnection() {
        try {
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            serverSocket = new ServerSocket(58100);
            FileLogger.log("ReceiveFileActivityPython", "Waiting for a connection...");
            clientSocket = serverSocket.accept();
            FileLogger.log("ReceiveFileActivityPython", "Connected to " + clientSocket.getInetAddress().getHostAddress());
            return true;
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error initializing connection", e);
            return false;
        }
    }

    private class ReceiveFilesTask implements Runnable {
        @Override
        public void run() {
            // Close any existing connections
            try {
                if (serverSocket != null && !serverSocket.isClosed()) {
                    serverSocket.close();
                }
            } catch (IOException e) {
                FileLogger.log("ReceiveFileActivityPython", "Error closing server socket", e);
            }
            receiveFiles();
            // Close threads and sockets after file reception
            if (clientSocket != null && !clientSocket.isClosed()) {
                try {
                    clientSocket.close();
                } catch (IOException e) {
                    FileLogger.log("ReceiveFileActivityPython", "Error closing client socket", e);
                }
            }
        }

        private void receiveFiles() {
            runOnUiThread(() -> {
                progressBar.setVisibility(ProgressBar.VISIBLE);
                waitingAnimation.setVisibility(LottieAnimationView.INVISIBLE);
                animationView.setVisibility(LottieAnimationView.VISIBLE);
                animationView.playAnimation();
            });
            FileLogger.log("ReceiveFileActivityPython", "File reception started.");
            try {
                // Load the save directory from the config file
                File configFile = new File(getFilesDir(), "config/config.json");
                saveToDirectory = loadSaveDirectoryFromConfig();
                FileLogger.log("ReceiveFileActivityPython", "Save directory: " + saveToDirectory);

                // Ensure the directory path is correctly formed
                File baseDir = Environment.getExternalStorageDirectory();
                File targetDir = new File(baseDir, saveToDirectory);

                // Create the directory if it doesn't exist
                if (!targetDir.exists() && !targetDir.mkdirs()) {
                    FileLogger.log("ReceiveFileActivityPython", "Failed to create directory: " + targetDir.getPath());
                    return;
                }

                destinationFolder = targetDir.getPath();
                JSONArray metadataArray = null;

                while (true) {
                    // Read encryption flag
                    byte[] encryptionFlagBytes = new byte[8];
                    clientSocket.getInputStream().read(encryptionFlagBytes);
                    String encryptionFlag = new String(encryptionFlagBytes).trim();

                    if (encryptionFlag.isEmpty() || encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {
                        FileLogger.log("ReceiveFileActivityPython", "Received all files.");
                        // After file reception is complete, update the UI accordingly
                        runOnUiThread(() -> {
                            txt_waiting.setText("File transfer completed");
                            progressBar.setProgress(0);
                            progressBar.setVisibility(ProgressBar.INVISIBLE);
                            animationView.setVisibility(LottieAnimationView.INVISIBLE);
                            txt_path.setText("Files saved to: " + destinationFolder);
                            txt_path.setVisibility(TextView.VISIBLE);
                        });
                        break;
                    }

                    // Read file name size
                    byte[] fileNameSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileNameSizeBytes);
                    long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileNameSize == 0) {
                        break;
                    }

                    // Read file name
                    byte[] fileNameBytes = new byte[(int) fileNameSize];
                    clientSocket.getInputStream().read(fileNameBytes);
                    String fileName = new String(fileNameBytes, StandardCharsets.UTF_8).replace('\\', '/');

                    // Read file size
                    byte[] fileSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileSizeBytes);
                    long fileSize = ByteBuffer.wrap(fileSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileSize < 0) {
                        continue;
                    }

                    // Handle metadata
                    if (fileName.equals("metadata.json")) {
                        metadataArray = receiveMetadata(fileSize);
                        if (metadataArray != null) {
                            destinationFolder = createFolderStructure(metadataArray, targetDir.getPath());
                        }
                        continue;
                    }

                    // Ensure destination file path is valid
                    String filePath = (metadataArray != null) ? getFilePathFromMetadata(metadataArray, fileName) : fileName;
                    File receivedFile = new File(destinationFolder, filePath);

                    // Check if received path is a directory
                    if (receivedFile.isDirectory()) {
                        FileLogger.log("ReceiveFileActivityPython", "Received path is a directory, removing filename from path.");
                        receivedFile = new File(destinationFolder, filePath + File.separator + fileName);
                    }

                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists() && !parentDir.mkdirs()) {
                        FileLogger.log("ReceiveFileActivityPython", "Failed to create directory: " + parentDir.getPath());
                        continue;
                    }

                    try {
                        String originalName = receivedFile.getName();
                        String nameWithoutExt;
                        String extension = "";

                        int dotIndex = originalName.lastIndexOf('.');
                        if (dotIndex == -1) {
                            // No extension found
                            nameWithoutExt = originalName;
                        } else {
                            // Split name and extension
                            nameWithoutExt = originalName.substring(0, dotIndex);
                            extension = originalName.substring(dotIndex);
                        }

                        int i = 1;
                        while (receivedFile.exists()) {
                            String newFileName = nameWithoutExt + " (" + i + ")" + extension;
                            receivedFile = new File(destinationFolder, newFileName);
                            i++;
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }

                    try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
                        byte[] buffer = new byte[4096];
                        long receivedSize = 0;

                        while (receivedSize < fileSize) {
                            int bytesRead = clientSocket.getInputStream().read(buffer, 0, (int) Math.min(buffer.length, fileSize - receivedSize));
                            if (bytesRead == -1) {
                                break;
                            }
                            fos.write(buffer, 0, bytesRead);
                            receivedSize += bytesRead;

                            int progress = (int) ((receivedSize * 100) / fileSize);
                            FileLogger.log("ReceiveFileActivityPython", "Received size: " + receivedSize + ", Progress: " + progress);
                            runOnUiThread(() -> progressBar.setProgress(progress));
                        }
                    }
                }
            } catch (IOException e) {
                FileLogger.log("ReceiveFileActivityPython", "Error receiving files", e);
            }
        }
    }

    public void startConnectionTask() {
        executorService.submit(new ConnectionTask());
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
                FileLogger.log("ReceiveFileActivityPython", "Error processing metadata for file: " + fileName, e);
            }
        }
        return fileName; // Return original fileName if not found in metadata
    }

    // Method to load the save directory from config.json
    // Updated loadSaveDirectoryFromConfig method
    private String loadSaveDirectoryFromConfig() {
        String saveToDirectory = "";
        File configFile = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config/config.json");

        try {
            FileLogger.log("ReceiveFileActivityPython", "Config file path: " + configFile.getAbsolutePath()); // Log the config path
            FileInputStream fis = new FileInputStream(configFile);
            BufferedReader reader = new BufferedReader(new InputStreamReader(fis));
            StringBuilder jsonBuilder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                jsonBuilder.append(line);
            }
            fis.close();
            JSONObject json = new JSONObject(jsonBuilder.toString());
            saveToDirectory = json.optString("saveToDirectory", "Download/DataDash");
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivityPython", "Error loading saveToDirectory from config", e);
            saveToDirectory = "Download/DataDash"; // Default if loading fails
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
            FileLogger.log("ReceiveFileActivityPython", "Error receiving metadata", e);
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error parsing metadata JSON", e);
        }
        return null; // Return null or handle accordingly if metadata reception fails
    }

    private String createFolderStructure(JSONArray metadataArray, String saveToDirectory) {
        if (metadataArray.length() == 0) {
            FileLogger.log("ReceiveFileActivityPython", "No metadata provided for folder structure.");
            return saveToDirectory; // Return saveToDirectory if no metadata
        }

        String topLevelFolder = ""; // Variable to hold the top-level folder name

        try {
            // Extract the base folder name from the last entry if available
            JSONObject lastMetadata = metadataArray.getJSONObject(metadataArray.length() - 1);
            topLevelFolder = lastMetadata.optString("base_folder_name", "");

            if (topLevelFolder.isEmpty()) {
                FileLogger.log("ReceiveFileActivityPython", "Base folder name not found in metadata, aborting folder creation.");
                return saveToDirectory; // Abort if no base folder name is found
            }
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error processing metadata JSON to extract base folder name", e);
            return saveToDirectory; // Fallback if there's an error
        }

        // Construct the top-level folder path
        String topLevelFolderPath = new File(saveToDirectory, topLevelFolder).getPath();
        FileLogger.log("ReceiveFileActivityPython", "Top-level folder path: " + topLevelFolderPath);

        // Check if the folder already exists and rename if necessary
        File topLevelDir = new File(topLevelFolderPath);
        if (topLevelDir.exists()) {
            // Increment the folder name if it already exists
            int i = 1;
            String newFolderName;
            do {
                newFolderName = topLevelFolder + " (" + i + ")";
                topLevelDir = new File(saveToDirectory, newFolderName);
                i++;
            } while (topLevelDir.exists());
            topLevelFolderPath = topLevelDir.getPath(); // Update to the new folder path
            FileLogger.log("ReceiveFileActivityPython", "Renamed existing folder to: " + topLevelFolderPath);
        } else {
            // Create the top-level folder
            if (!topLevelDir.mkdirs()) {
                FileLogger.log("ReceiveFileActivityPython", "Failed to create top-level folder: " + topLevelFolderPath);
                return saveToDirectory; // Fallback if folder creation fails
            }
            FileLogger.log("ReceiveFileActivityPython", "Created top-level folder: " + topLevelFolderPath);
        }

        // Process each file info in the metadata array
        for (int i = 0; i < metadataArray.length(); i++) {
            try {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String filePath = fileInfo.optString("path", "");
                if (filePath.equals(".delete")) {
                    continue; // Skip paths marked for deletion
                }

                // Handle case where the path is provided in metadata
                File fullFilePath = new File(topLevelFolderPath, filePath); // Prepend top-level folder
                File parentDir = fullFilePath.getParentFile();
                if (parentDir != null && !parentDir.exists()) {
                    parentDir.mkdirs(); // Create the folder structure if it doesn't exist
                    FileLogger.log("ReceiveFileActivityPython", "Created folder: " + parentDir.getPath());
                }
            } catch (JSONException e) {
                FileLogger.log("ReceiveFileActivityPython", "Error processing file info in metadata", e);
                // Continue to the next file if there's an error with the current one
            }
        }

        return topLevelFolderPath; // Return the path of the created folder structure
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
            FileLogger.log("ReceiveFileActivityPython", "Error closing sockets", e);
        }
    }

    @Override
    public void onBackPressed() {
        super.onBackPressed();
        // Close sockets on activity destruction
        try {
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
            }
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error closing sockets", e);
        }
        finish();
    }
}