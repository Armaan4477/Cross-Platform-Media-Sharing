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
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
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
    private Button donebtn;
    private TextView txt_path;
    private boolean isEncryptedTransfer;
    private ArrayList<String> encryptedFiles = new ArrayList<String>();
    private ExecutorService executorService = Executors.newFixedThreadPool(2); // Using 2 threads: one for connection, one for file reception
    private static final int PORT = 57341;
    private static final int MAX_RETRIES = 3;
    private static final int RETRY_DELAY_MS = 1000;
    private static final int SOCKET_TIMEOUT = 30000; // 30 seconds
    private static final int BUFFER_SIZE = 4096;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                new AlertDialog.Builder(ReceiveFileActivityPython.this)
                        .setTitle("Exit")
                        .setMessage("Are you sure you want to cancel the transfer?")
                        .setPositiveButton("Yes", (dialog, which) -> {
                            dialog.dismiss();
                            closeAllSockets();
                            forceReleasePort();
                            Toast.makeText(ReceiveFileActivityPython.this, "Device Disconnected", Toast.LENGTH_SHORT).show();
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
            FileLogger.log("ReceiveFileActivityPython", "Failed to retrieve OS type", e);
        }

        if(osType.equals("Windows")) {
            txt_waiting.setText("Waiting to receive files from a Windows device");
        } else if (osType.equals("Linux")) {
            txt_waiting.setText("Waiting to receive files from a Linux device");
        } else if (osType.equals("Darwin")) {
            txt_waiting.setText("Waiting to receive files from a macOS device");
        } else {
            txt_waiting.setText("Waiting to receive files from Desktop app");
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
                        txt_waiting.setText("Receiving files from a Windows device");
                    } else if (osType.equals("Linux")) {
                        txt_waiting.setText("Receiving files from a Linux device");
                    } else if (osType.equals("Darwin")) {
                        txt_waiting.setText("Receiving files from a macOS device");
                    } else {
                        txt_waiting.setText("Receiving files from Desktop app");
                    }
                    executorService.submit(new ReceiveFilesTask()); // Submit ReceiveFilesTask to executorService
                } else {
                    FileLogger.log("ReceiveFileActivityPython", "Failed to establish connection.");
                }
            });
        }
    }


    private boolean initializeConnection() {
        int retryCount = 0;

        while (retryCount < MAX_RETRIES) {
            try {
                // Cleanup existing sockets
                cleanupSockets();

                // Create new server socket
                serverSocket = new ServerSocket();
                serverSocket.setReuseAddress(true);
                serverSocket.setSoTimeout(SOCKET_TIMEOUT);
                serverSocket.bind(new InetSocketAddress(PORT));

                FileLogger.log("ReceiveFileActivityPython", "Listening on port: " + PORT);

                // Accept connection
                clientSocket = serverSocket.accept();
                clientSocket.setSoTimeout(SOCKET_TIMEOUT);

                FileLogger.log("ReceiveFileActivityPython",
                        "Connected to " + clientSocket.getInetAddress().getHostAddress());
                return true;

            } catch (IOException e) {
                FileLogger.log("ReceiveFileActivityPython",
                        "Connection attempt " + (retryCount + 1) + " failed: " + e.getMessage());
                retryCount++;

                if (retryCount < MAX_RETRIES) {
                    try {
                        Thread.sleep(RETRY_DELAY_MS);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        return false;
                    }
                }
            }
        }
        return false;
    }

    private void cleanupSockets() {
        try {
            if (clientSocket != null && !clientSocket.isClosed()) {
                clientSocket.close();
            }
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            Thread.sleep(RETRY_DELAY_MS);
        } catch (IOException | InterruptedException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error during socket cleanup: " + e.getMessage());
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
                    int bytesRead = clientSocket.getInputStream().read(encryptionFlagBytes);
                    if (bytesRead <= 0) {
                        FileLogger.log("ReceiveFileActivityPython", "Connection closed by sender");
                        break;
                    }
                    
                    String encryptionFlag = new String(encryptionFlagBytes).trim();
                    FileLogger.log("ReceiveFileActivityPython", "Received encryption flag: " + encryptionFlag);

                    if (encryptionFlag.equals("encyp: h")) {
                        FileLogger.log("ReceiveFileActivityPython", "Received halt signal");
                        
                        if (isEncryptedTransfer) {
                            // Handle encrypted files
                            Intent intent = new Intent(ReceiveFileActivityPython.this, Decryptor.class);
                            intent.putStringArrayListExtra("files", encryptedFiles);
                            startActivity(intent);
                        }

                        // Update UI for completion
                        runOnUiThread(() -> {
                            txt_waiting.setText("File transfer completed");
                            progressBar.setProgress(0);
                            progressBar.setVisibility(ProgressBar.INVISIBLE);
                            animationView.setVisibility(LottieAnimationView.INVISIBLE);
                            txt_path.setText("Files saved to: " + destinationFolder);
                            txt_path.setVisibility(TextView.VISIBLE);
//                            donebtn.setVisibility(Button.VISIBLE);
                        });
                        break;
                    }

                    isEncryptedTransfer = encryptionFlag.equals("encyp: t");

                    // Read file name size
                    byte[] fileNameSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileNameSizeBytes);
                    long fileNameSize = ByteBuffer.wrap(fileNameSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    // Read file name
                    byte[] fileNameBytes = new byte[(int) fileNameSize];
                    clientSocket.getInputStream().read(fileNameBytes);
                    String fileName = new String(fileNameBytes, StandardCharsets.UTF_8);

                    // Read file size
                    byte[] fileSizeBytes = new byte[8];
                    clientSocket.getInputStream().read(fileSizeBytes);
                    long fileSize = ByteBuffer.wrap(fileSizeBytes).order(ByteOrder.LITTLE_ENDIAN).getLong();

                    // Process metadata.json
                    if (fileName.equals("metadata.json")) {
                        metadataArray = receiveMetadata(fileSize);
                        if (metadataArray != null) {
                            destinationFolder = createFolderStructure(metadataArray, targetDir.getPath());
                        }
                        continue;
                    }

                    // Create file path based on relative path
                    File receivedFile = new File(destinationFolder, fileName);
                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists()) {
                        parentDir.mkdirs();
                    }

                    // Handle file naming conflicts
                    receivedFile = handleFileConflict(receivedFile);

                    // Receive file data
                    try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
                        byte[] buffer = new byte[BUFFER_SIZE];
                        long receivedSize = 0;

                        while (receivedSize < fileSize) {
                            int read = clientSocket.getInputStream().read(buffer, 0, 
                                (int) Math.min(buffer.length, fileSize - receivedSize));
                            if (read == -1) break;
                            fos.write(buffer, 0, read);
                            receivedSize += read;

                            int progress = (int) ((receivedSize * 100) / fileSize);
                            runOnUiThread(() -> progressBar.setProgress(progress));
                        }
                    }

                    if (isEncryptedTransfer) {
                        encryptedFiles.add(receivedFile.getPath());
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
            InputStream in = clientSocket.getInputStream();
            int totalBytesRead = 0;
            while (totalBytesRead < fileSize) {
                int bytesRead = in.read(receivedData, totalBytesRead, (int) (fileSize - totalBytesRead));
                if (bytesRead == -1) {
                    break; // End of stream reached
                }
                totalBytesRead += bytesRead;
            }
            String metadataJson = new String(receivedData, 0, totalBytesRead, StandardCharsets.UTF_8);
            return new JSONArray(metadataJson);
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error receiving metadata", e);
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error parsing metadata JSON", e);
        }
        return null;
    }

    private String createFolderStructure(JSONArray metadataArray, String basePath) {
        try {
            // Normalize base path
            basePath = basePath.replace('\\', '/');
            
            String baseFolderName = null;
            for (int i = 0; i < metadataArray.length(); i++) {
                JSONObject entry = metadataArray.getJSONObject(i);
                if (entry.has("base_folder_name")) {
                    baseFolderName = entry.getString("base_folder_name");
                    break;
                }
            }

            if (baseFolderName == null) {
                return basePath;
            }

            // Create base folder with conflict handling
            File baseFolder = new File(basePath, baseFolderName);
            baseFolder = handleFileConflict(baseFolder);
            baseFolder.mkdirs();

            // Create all directories from metadata
            for (int i = 0; i < metadataArray.length(); i++) {
                JSONObject entry = metadataArray.getJSONObject(i);
                String path = entry.getString("path").replace('\\', '/');
                
                if (path.equals(".delete")) continue;
                
                if (path.endsWith("/")) {
                    // It's a directory
                    File dir = new File(baseFolder, path);
                    dir.mkdirs();
                }
            }

            return baseFolder.getAbsolutePath().replace('\\', '/');
        } catch (JSONException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error processing metadata", e);
            return basePath;
        }
    }

    private File handleFileConflict(File file) {
        // Normalize the file path
        file = new File(file.getAbsolutePath().replace('\\', '/'));
        
        if (!file.exists()) return file;

        String name = file.getName();
        String parent = file.getParent();
        String nameNoExt = name;
        String extension = "";

        int dotIndex = name.lastIndexOf('.');
        if (dotIndex > 0) {
            nameNoExt = name.substring(0, dotIndex);
            extension = name.substring(dotIndex);
        }

        int counter = 1;
        File newFile;
        do {
            newFile = new File(parent, nameNoExt + " (" + counter + ")" + extension);
            counter++;
        } while (newFile.exists());

        return newFile;
    }

    private void ondonebtnclk(){
        Toast.makeText(this, "App Exit Completed", Toast.LENGTH_SHORT).show();
        finishAffinity(); // Close all activities
        android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
        System.exit(0); // Ensure complete shutdown
    }

    private void forceReleasePort() {
        int port1 =PORT;
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
                FileLogger.log("ReceiveFileActivityPython", "Client Socket closed");
            }
            
            // Close server socket
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
                FileLogger.log("ReceiveFileActivityPython", "Server Socket closed");
            }

            // Shutdown executor service
            if (executorService != null && !executorService.isShutdown()) {
                executorService.shutdown();
                FileLogger.log("ReceiveFileActivityPython", "ExecutorService shutdown");
            }

            finish(); // Close the activity
        } catch (IOException e) {
            FileLogger.log("ReceiveFileActivityPython", "Error closing sockets", e);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeAllSockets();
    }
}