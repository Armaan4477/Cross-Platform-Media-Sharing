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
    private LottieAnimationView animationView;
    private LottieAnimationView waitingAnimation;
    private Button openFolder;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);
        progressBar = findViewById(R.id.fileProgressBar);
        txt_waiting = findViewById(R.id.txt_waiting);
        animationView = findViewById(R.id.transfer_animation);
        waitingAnimation = findViewById(R.id.waiting_animation);
        openFolder = findViewById(R.id.openFolder);

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
        protected void onPreExecute() {
            // Show animation when sending starts
            progressBar.setVisibility(ProgressBar.VISIBLE);
            waitingAnimation.setVisibility(LottieAnimationView.INVISIBLE);
            animationView.setVisibility(LottieAnimationView.VISIBLE);
            animationView.playAnimation();
        }

        @Override
        protected void onProgressUpdate(Integer... values) {
            progressBar.setProgress(values[0]);
        }

        @Override
        protected void onPostExecute(Void result) {
            txt_waiting.setText("File transfer completed");
            progressBar.setProgress(0);
            progressBar.setVisibility(ProgressBar.INVISIBLE);
            animationView.setVisibility(LottieAnimationView.INVISIBLE);
            openFolder.setVisibility(Button.VISIBLE);

            openFolder.setOnClickListener(v -> {
                // Create a File object for the destination folder
                File folder = new File(destinationFolder);

                Log.d("ReceiveFileActivity", "Opening folder: " + folder.getPath());
                if (folder.exists() && folder.isDirectory()) {
                    try {
                        // Create an intent to view the folder
                        Intent intent = new Intent(Intent.ACTION_VIEW);
                        Uri folderUri;

                        // Use FileProvider if targeting Android 7.0 (API level 24) or higher
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                            // Use FileProvider for API 24 and above
                            folderUri = FileProvider.getUriForFile(
                                    ReceiveFileActivity.this,
                                    getApplicationContext().getPackageName() + ".provider",
                                    folder
                            );
                            intent.setDataAndType(folderUri, "*/*");
                            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        } else {
                            // Use direct file URI for earlier versions
                            folderUri = Uri.fromFile(folder);
                            intent.setDataAndType(folderUri, "*/*");
                        }

                        // Add flags to minimize the current app and open the file manager
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

                        // Start the file manager without expecting a result
                        startActivity(intent);
                        // Optionally, call finish() to close the current activity
                        finish();
                    } catch (IllegalArgumentException e) {
                        Log.e("ReceiveFileActivity", "FileProvider error: " + e.getMessage());
                    }
                } else {
                    Log.e("ReceiveFileActivity", "Directory does not exist: " + destinationFolder);
                }
            });
        }

        private void receiveFiles() {
            Log.d("ReceiveFileActivity", "File reception started.");
            try {
                // Load the save directory from the config file
                File configFile = new File(getFilesDir(), "config/config.json");
                saveToDirectory = loadSaveDirectoryFromConfig(configFile);
                Log.d("ReceiveFileActivity", "Save directory: " + saveToDirectory);

                // Ensure the directory path is correctly formed
                File baseDir = Environment.getExternalStorageDirectory();
                File targetDir = new File(baseDir, saveToDirectory);

                // Create the directory if it doesn't exist
                if (!targetDir.exists() && !targetDir.mkdirs()) {
                    Log.e("ReceiveFileActivityPython", "Failed to create directory: " + targetDir.getPath());
                    return;
                }

                destinationFolder = targetDir.getPath(); // Update destinationFolder to the newly formed path
                JSONArray metadataArray = null;

                while (true) {
                    // Read encryption flag
                    byte[] encryptionFlagBytes = new byte[8];
                    clientSocket.getInputStream().read(encryptionFlagBytes);
                    String encryptionFlag = new String(encryptionFlagBytes).trim();

                    if (encryptionFlag.isEmpty() || encryptionFlag.charAt(encryptionFlag.length() - 1) == 'h') {
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
                        Log.e("ReceiveFileActivity", "Received path is a directory, removing filename from path.");
                        receivedFile = new File(destinationFolder, filePath + File.separator + fileName);
                    }

                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists() && !parentDir.mkdirs()) {
                        Log.e("ReceiveFileActivity", "Failed to create directory: " + parentDir.getPath());
                        continue;
                    }

                    // Rename file if it already exists
                    String originalName = receivedFile.getName();
                    String nameWithoutExt = originalName.substring(0, originalName.lastIndexOf('.'));
                    String extension = originalName.substring(originalName.lastIndexOf('.'));
                    int i = 1;

                    // Check if the file exists in the receiving directory
                    while (receivedFile.exists()) {
                        String newFileName = nameWithoutExt + " (" + i + ")" + extension;
                        receivedFile = new File(destinationFolder, newFileName);
                        i++;
                    }

                    try (FileOutputStream fos = new FileOutputStream(receivedFile)) {
                        byte[] buffer = new byte[4096 * 4]; // Increased buffer size for faster transfer
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
                            Log.d("ReceiveFileActivityPython", "Received size: " + receivedSize + ", Progress: " + progress);
                            publishProgress(progress);
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
        return fileName; // Return original fileName if not found in metadata
    }

    // Method to load the save directory from config.json
    private String loadSaveDirectoryFromConfig(File configFile) {
        String saveToDirectory = ""; // Use an empty string as the initial value
        try {
            // Load config.json
            configFile = new File(getFilesDir(), "config/config.json");
            FileInputStream fis = new FileInputStream(configFile);
            BufferedReader reader = new BufferedReader(new InputStreamReader(fis));
            StringBuilder jsonBuilder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                jsonBuilder.append(line);
            }
            reader.close();
            JSONObject config = new JSONObject(jsonBuilder.toString());
            saveToDirectory = config.optString("save_to_directory", "");
            saveToDirectory = saveToDirectory.startsWith("/") ? saveToDirectory.substring(1) : saveToDirectory; // Remove leading '/'
        } catch (Exception e) {
            Log.e("ReceiveFileActivityPython", "Error loading config.json", e);
        }
        Log.d("ReceiveFileActivityPython", "Loaded save directory: " + saveToDirectory);
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