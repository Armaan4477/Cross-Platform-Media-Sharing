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
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import com.airbnb.lottie.LottieAnimationView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
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
    private LottieAnimationView animationView;
    private LottieAnimationView waitingAnimation;
    private Button openFolder;
    private TextView txt_path;
    private final ExecutorService executorService = Executors.newFixedThreadPool(2);

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
            Log.e("ReceiveFileActivity", "Failed to retrieve OS type", e);
        }

        txt_waiting.setText("Waiting to receive file from Android");

        startConnectionTask();
    }

    public void startConnectionTask() {
        executorService.execute(new ConnectionTask());
    }

    private class ConnectionTask implements Runnable {
        @Override
        public void run() {
            boolean connectionSuccessful = initializeConnection();
            if (connectionSuccessful) {
                Log.d("ReceiveFileActivity", "Connection established with the sender.");
                txt_waiting.setText("Receiving files from " + deviceType);
                startReceiveFilesTask();
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

    public void startReceiveFilesTask() {
        executorService.execute(new ReceiveFilesTask());
    }

    @SuppressLint("StaticFieldLeak")
    private class ReceiveFilesTask implements Runnable {
        @Override
        public void run() {
            receiveFiles();
        }

        private void receiveFiles() {
            runOnUiThread(() -> {
                progressBar.setVisibility(ProgressBar.VISIBLE);
                waitingAnimation.setVisibility(LottieAnimationView.INVISIBLE);
                animationView.setVisibility(LottieAnimationView.VISIBLE);
                animationView.playAnimation();
            });
            Log.d("ReceiveFileActivity", "File reception started.");
            try {
                File configFile = new File(getFilesDir(), "config/config.json");
                saveToDirectory = loadSaveDirectoryFromConfig();
                Log.d("ReceiveFileActivity", "Save directory: " + saveToDirectory);

                File baseDir = Environment.getExternalStorageDirectory();
                File targetDir = new File(baseDir, saveToDirectory);

                if (!targetDir.exists() && !targetDir.mkdirs()) {
                    Log.e("ReceiveFileActivityPython", "Failed to create directory: " + targetDir.getPath());
                    return;
                }

                destinationFolder = targetDir.getPath();
                JSONArray metadataArray = null;

                while (true) {
                    byte[] encryptionFlagBytes = new byte[8];
                    clientSocket.getInputStream().read(encryptionFlagBytes);
                    String encryptionFlag = new String(encryptionFlagBytes).trim();

                    if (encryptionFlag.isEmpty() || encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {
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
                            destinationFolder = createFolderStructure(metadataArray, targetDir.getPath());
                        }
                        continue;
                    }

                    String filePath = (metadataArray != null) ? getFilePathFromMetadata(metadataArray, fileName) : fileName;
                    File receivedFile = new File(destinationFolder, filePath);

                    if (receivedFile.isDirectory()) {
                        Log.e("ReceiveFileActivity", "Received path is a directory, removing filename from path.");
                        receivedFile = new File(destinationFolder, filePath + File.separator + fileName);
                    }
                    Log.d("ReceiveFileActivity", "Receiving file: " + receivedFile.getPath());

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
                            Log.d("ReceiveFileActivityPython", "Received size: " + receivedSize + ", Progress: " + progress);
                            runOnUiThread(() -> progressBar.setProgress(progress));
                        }
                    }
                }
            } catch (IOException e) {
                Log.e("ReceiveFileActivityPython", "Error receiving files", e);
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
        return fileName;
    }

    // Method to load the save directory from config.json
    // Updated loadSaveDirectoryFromConfig method
    private String loadSaveDirectoryFromConfig() {
        String saveToDirectory = "";
        File configFile = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config/config.json");

        try {
            Log.e("ReceiveFileActivityPython", "Config file path: " + configFile.getAbsolutePath()); // Log the config path
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
            Log.e("ReceiveFileActivityPython", "Error loading saveToDirectory from config", e);
            saveToDirectory = "Download/DataDash"; // Default if loading fails
        }
        return saveToDirectory;
    }

    private JSONArray receiveMetadata(long fileSize) {
        JSONArray metadataArray = null;
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            long receivedSize = 0;
            while (receivedSize < fileSize) {
                int bytesRead = clientSocket.getInputStream().read(buffer, 0, (int) Math.min(buffer.length, fileSize - receivedSize));
                if (bytesRead == -1) {
                    break;
                }
                baos.write(buffer, 0, bytesRead);
                receivedSize += bytesRead;
            }
            String metadataJson = baos.toString(StandardCharsets.UTF_8);
            metadataArray = new JSONArray(metadataJson);
        } catch (IOException | JSONException e) {
            Log.e("ReceiveFileActivity", "Error receiving metadata", e);
        }
        return metadataArray;
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
            if (lastMetadata.optString("base_folder_name", "").contains("primary")) {
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

        // Check if the top-level folder has primary in it
        if (topLevelFolder.contains("primary")) {
            topLevelFolder = topLevelFolder.replace("primary%3A", ""); // Remove primary%3A from the folder name
        }
        if(topLevelFolder.contains("%2F")) {
            // Keep string after last instance of %2F
            topLevelFolder = topLevelFolder.substring(topLevelFolder.lastIndexOf("%2F") + 3);
        }

        // Construct the destination folder path
        String destinationFolder = new File(defaultDir, topLevelFolder).getPath();
        Log.d("ReceiveFileActivity", "Destination folder: " + destinationFolder);

        File destinationDir = new File(destinationFolder);
        if (!destinationDir.exists()) {
            destinationDir.mkdirs(); // Create the base folder if it doesn't exist
            Log.d("ReceiveFileActivity", "Created base folder: " + destinationFolder);
        } else {
            // If the folder already exists, rename it by appending (i)
            int i = 1;
            String newFolderName = topLevelFolder + " (" + i + ")";
            File renamedFolder = new File(defaultDir, newFolderName);
            while (renamedFolder.exists()) {
                i++;
                newFolderName = topLevelFolder + " (" + i + ")";
                renamedFolder = new File(defaultDir, newFolderName);
            }
            // Create the new folder with the incremented name
            renamedFolder.mkdirs();
            Log.d("ReceiveFileActivity", "Renamed existing folder and created new folder: " + renamedFolder.getPath());
            destinationFolder = renamedFolder.getPath(); // Update destinationFolder to the new path
        }

        // Process each file info in the metadata array
        for (int i = 0; i < metadataArray.length() - 1; i++) { // Exclude the last entry
            try {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String filePath = fileInfo.optString("path", "");
                if (filePath.equals(".delete")) {
                    continue; // Skip paths marked for deletion
                }

                // Handle creating the folder structure for files
                File folderPath = new File(destinationFolder, filePath).getParentFile();
                if (folderPath != null && !folderPath.exists()) {
                    folderPath.mkdirs(); // Create the folder structure if it doesn't exist
                    Log.d("ReceiveFileActivity", "Created folder: " + folderPath.getPath());}
            } catch (JSONException e) {
                Log.e("ReceiveFileActivity", "Error processing file info in metadata", e);
                // Continue to the next file if there's an error with the current one
            }
        }
        return destinationFolder;
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
            Log.e("ReceiveFileActivityPython", "Error closing sockets", e);
        }
        finish();
    }
}