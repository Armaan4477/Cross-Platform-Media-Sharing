package com.an.crossplatform;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
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

import androidx.activity.OnBackPressedCallback;
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
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
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
    private Button donebtn;
    private TextView txt_path;
    private boolean isEncryptedTransfer;
    private ArrayList<String> encryptedFiles = new ArrayList<String>();
    private final ExecutorService executorService = Executors.newFixedThreadPool(2);
    private static final int FILE_TRANSFER_PORT = 63152;
    private static final int BUFFER_SIZE = 4096;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                new AlertDialog.Builder(ReceiveFileActivity.this)
                        .setTitle("Exit")
                        .setMessage("Are you sure you want to cancel the transfer?")
                        .setPositiveButton("Yes", (dialog, which) -> {
                            dialog.dismiss();
                            closeAllSockets();
                            forceReleasePort();
                            Toast.makeText(ReceiveFileActivity.this, "Device Disconnected", Toast.LENGTH_SHORT).show();
                        })
                        .setNegativeButton("No", (dialog, which) -> dialog.dismiss())
                        .show();
            }
        });

        progressBar = findViewById(R.id.fileProgressBar);
        txt_waiting = findViewById(R.id.txt_waiting);
        animationView = findViewById(R.id.transfer_animation);
        waitingAnimation = findViewById(R.id.waiting_animation);
        openFolder = findViewById(R.id.openFolder);
//        donebtn = findViewById(R.id.donebtn);
//        donebtn.setOnClickListener(v -> ondonebtnclk());
        txt_path = findViewById(R.id.path);

        senderJson = getIntent().getStringExtra("receivedJson");
        senderIp = getIntent().getStringExtra("senderIp");

        try {
            JSONObject jsonObject = new JSONObject(senderJson);
            osType = jsonObject.getString("os");
            deviceType = jsonObject.getString("device_type");
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivity", "Failed to retrieve OS type", e);
        }

        txt_waiting.setText("Waiting to receive files from Android");

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
                FileLogger.log("ReceiveFileActivity", "Connection established with the sender.");
                txt_waiting.setText("Receiving files from Android");
                startReceiveFilesTask();
            } else {
                FileLogger.log("ReceiveFileActivity", "Failed to establish connection.");
            }
        }
    }

    private boolean initializeConnection() {
        try {
            serverSocket = new ServerSocket();
            serverSocket.setReuseAddress(true);
            serverSocket.bind(new InetSocketAddress(FILE_TRANSFER_PORT));

            FileLogger.log("ReceiveFileActivity", "Starting server on port " + FILE_TRANSFER_PORT);
            clientSocket = serverSocket.accept();
            return true;
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivity", "Error initializing connection", e);
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
            try {
                receiveFiles();
            } finally {
                // Ensure sockets are properly closed
                try {
                    if (clientSocket != null) {
                        clientSocket.close();
                    }
                    if (serverSocket != null) {
                        serverSocket.close();
                    }
                } catch (IOException e) {
                    FileLogger.log("ReceiveFileActivity", "Error closing sockets", e);
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

            try {
                saveToDirectory = loadSaveDirectoryFromConfig();
                FileLogger.log("ReceiveFileActivity", "Save directory: " + saveToDirectory);

                File baseDir = Environment.getExternalStorageDirectory();
                File targetDir = new File(baseDir, saveToDirectory);

                if (!targetDir.exists() && !targetDir.mkdirs()) {
                    FileLogger.log("ReceiveFileActivity", "Failed to create directory: " + targetDir.getPath());
                    return;
                }

                JSONArray metadataArray = null;

                while (true) {
                    byte[] encryptionFlagBytes = new byte[8];
                    clientSocket.getInputStream().read(encryptionFlagBytes);
                    String encryptionFlag = new String(encryptionFlagBytes).trim();

                    if (encryptionFlag.isEmpty() || encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {

                        if (isEncryptedTransfer) {
                            // Handle encrypted files
                            Intent intent = new Intent(ReceiveFileActivity.this, Decryptor.class);
                            intent.putStringArrayListExtra("files", encryptedFiles);
                            startActivity(intent);
                        }
                        runOnUiThread(() -> {
                            txt_waiting.setText("File transfer completed");
                            progressBar.setProgress(0);
                            progressBar.setVisibility(ProgressBar.INVISIBLE);
                            animationView.setVisibility(LottieAnimationView.INVISIBLE);
                            txt_path.setText("Files saved to: " + destinationFolder);
                            txt_path.setVisibility(TextView.VISIBLE);
                            donebtn.setVisibility(Button.VISIBLE);
                        });
                        break;
                    }

                    isEncryptedTransfer = encryptionFlag.equals("encyp: t");

                    byte[] fileNameSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileNameSizeBytes);
                    long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileNameSize == 0) break;

                    byte[] fileNameBytes = new byte[(int) fileNameSize];
                    clientSocket.getInputStream().read(fileNameBytes);
                    String fileName = new String(fileNameBytes, StandardCharsets.UTF_8);

                    byte[] fileSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileSizeBytes);
                    long fileSize = ByteBuffer.wrap(fileSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    if (fileSize < 0) continue;

                    if (fileName.equals("metadata.json")) {
                        metadataArray = receiveMetadata(fileSize);
                        if (metadataArray != null) {
                            destinationFolder = createFolderStructure(metadataArray, targetDir.getPath());
                        }
                        continue;
                    }

                    if (metadataArray != null && destinationFolder != null) {
                        handleFilePath(fileName, destinationFolder, metadataArray, fileSize);

                    } else {
                        FileLogger.log("ReceiveFileActivity", "Missing metadata or destination folder");
                    }
                }
            } catch (IOException e) {
                FileLogger.log("ReceiveFileActivity", "Error receiving files", e);
            }
        }

        // Add this new method to ReceiveFileActivity.java
        private void handleFilePath(String fileName, String destinationFolder, JSONArray metadataArray, long fileSize) {
            try {
                // Get full path from metadata
                String filePath = getFilePathFromMetadata(metadataArray, fileName);
                FileLogger.log("ReceiveFileActivity", "Original file path: " + filePath);

                // Extract base folder name from first folder entry
                String baseFolderName = null;
                for (int i = 0; i < metadataArray.length(); i++) {
                    JSONObject fileInfo = metadataArray.getJSONObject(i);
                    String path = fileInfo.optString("path", "");
                    if (path.endsWith("/")) {
                        baseFolderName = path.substring(0, path.indexOf("/"));
                        FileLogger.log("ReceiveFileActivity", "Found base folder name: " + baseFolderName);
                        break;
                    }
                }

                // Strip base folder name from path
                if (baseFolderName != null && filePath.startsWith(baseFolderName + "/")) {
                    filePath = filePath.substring(baseFolderName.length() + 1);
                    FileLogger.log("ReceiveFileActivity", "Adjusted file path: " + filePath);
                }

                // Create file and ensure parent directories exist
                File receivedFile = new File(destinationFolder, filePath);
                File parentDir = receivedFile.getParentFile();
                if (parentDir != null && !parentDir.exists()) {
                    boolean created = parentDir.mkdirs();
                    FileLogger.log("ReceiveFileActivity", "Created parent directory: " + created);
                }

                // Handle duplicate file names
                String fileNameWithoutExt = receivedFile.getName();
                String extension = "";
                int dotIndex = fileNameWithoutExt.lastIndexOf('.');
                if (dotIndex > 0) {
                    extension = fileNameWithoutExt.substring(dotIndex);
                    fileNameWithoutExt = fileNameWithoutExt.substring(0, dotIndex);
                }

                int counter = 1;
                while (receivedFile.exists()) {
                    String newFileName = fileNameWithoutExt + " (" + counter + ")" + extension;
                    receivedFile = new File(parentDir, newFileName);
                    counter++;
                }

                FileLogger.log("ReceiveFileActivity", "Writing file to: " + receivedFile.getAbsolutePath());

                // Write file data
                try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
                    byte[] buffer = new byte[BUFFER_SIZE];
                    long receivedSize = 0;

                    while (receivedSize < fileSize) {
                        int bytesRead = clientSocket.getInputStream().read(buffer, 0,
                                (int) Math.min(buffer.length, fileSize - receivedSize));
                        if (bytesRead == -1) break;

                        fos.write(buffer, 0, bytesRead);
                        receivedSize += bytesRead;

                        int progress = (int) ((receivedSize * 100) / fileSize);
                        runOnUiThread(() -> progressBar.setProgress(progress));
                    }
                }

                FileLogger.log("ReceiveFileActivity", "File written successfully: " + receivedFile.getName());

                if (isEncryptedTransfer) {
                    encryptedFiles.add(receivedFile.getPath());
                    Log.d("ReceiveFileActivityPython", "Received encrypted file: " + receivedFile.getPath());
                }
            } catch (IOException | JSONException e) {
                FileLogger.log("ReceiveFileActivity", "Error handling file path: " + fileName, e);
            }
        }
    }

    private String getFilePathFromMetadata(JSONArray metadataArray, String fileName) {
        for (int i = 0; i < metadataArray.length(); i++) {
            try {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String path = fileInfo.optString("path", "");
                if (!path.endsWith("/") && path.endsWith(fileName)) {
                    return path;
                }
            } catch (JSONException e) {
                FileLogger.log("ReceiveFileActivity", "Error processing metadata for file: " + fileName, e);
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
        JSONArray metadataArray = null;
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[BUFFER_SIZE];
            long receivedSize = 0;
            while (receivedSize < fileSize) {
                int bytesRead = clientSocket.getInputStream().read(buffer, 0, (int) Math.min(buffer.length, fileSize - receivedSize));
                if (bytesRead == -1) {
                    break;
                }
                baos.write(buffer, 0, bytesRead);
                receivedSize += bytesRead;
            }
            String metadataJson = new String(baos.toByteArray(), StandardCharsets.UTF_8);
            metadataArray = new JSONArray(metadataJson);
        } catch (IOException | JSONException e) {
            FileLogger.log("ReceiveFileActivity", "Error receiving metadata", e);
        }
        return metadataArray;
    }

    // In ReceiveFileActivity.java - Update createFolderStructure method
    private String createFolderStructure(JSONArray metadataArray, String defaultDir) {
        if (metadataArray.length() == 0) {
            FileLogger.log("ReceiveFileActivity", "Empty metadata array");
            return defaultDir;
        }

        try {
            // Extract base folder name from paths
            String baseFolderName = null;
            for (int i = 0; i < metadataArray.length(); i++) {
                JSONObject fileInfo = metadataArray.getJSONObject(i);
                String path = fileInfo.optString("path", "");
                if (path.endsWith("/")) {
                    baseFolderName = path.substring(0, path.indexOf("/"));
                    FileLogger.log("ReceiveFileActivity", "Found base folder name: " + baseFolderName);
                    break;
                }
            }

            if (baseFolderName == null || baseFolderName.isEmpty()) {
                FileLogger.log("ReceiveFileActivity", "Could not determine base folder name");
                return defaultDir;
            }

            // Handle duplicate folder names for root folder only
            String finalFolderName = baseFolderName;
            File destinationDir = new File(defaultDir, finalFolderName);
            int counter = 1;

            while (destinationDir.exists()) {
                finalFolderName = baseFolderName + " (" + counter + ")";
                destinationDir = new File(defaultDir, finalFolderName);
                counter++;
                FileLogger.log("ReceiveFileActivity", "Trying folder name: " + finalFolderName);
            }

            // Create the root folder
            String destinationFolder = destinationDir.getAbsolutePath();
            if (!destinationDir.mkdirs()) {
                FileLogger.log("ReceiveFileActivity", "Failed to create directory: " + destinationFolder);
                if (!destinationDir.exists()) {
                    return defaultDir;
                }
            }
            FileLogger.log("ReceiveFileActivity", "Created root folder: " + destinationFolder);

            // Update base folder name to include numbering if needed
            baseFolderName = finalFolderName;

            return destinationFolder;

        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivity", "Error processing metadata JSON", e);
            return defaultDir;
        }
    }

    private void ondonebtnclk(){
        Toast.makeText(this, "App Exit Completed", Toast.LENGTH_SHORT).show();
        finishAffinity(); // Close all activities
        android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
        System.exit(0); // Ensure complete shutdown
    }

    private void forceReleasePort() {
        int port1 =FILE_TRANSFER_PORT;
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port1);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port1);
                    }
                }
            }

            // Wait briefly for port to be fully released
            Thread.sleep(500);
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port1, e);
        }
    }

    private void closeAllSockets() {
        try {
            // Close client socket
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
                FileLogger.log("ReceiveFileActivity", "Client Socket closed");
            }
            
            // Close server socket
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
                FileLogger.log("ReceiveFileActivity", "Server Socket closed");
            }

            // Shutdown executor service
            if (executorService != null && !executorService.isShutdown()) {
                executorService.shutdown();
                FileLogger.log("ReceiveFileActivity", "ExecutorService shutdown");
            }

            finish(); // Close the activity
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivity", "Error closing sockets", e);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeAllSockets();
    }
}