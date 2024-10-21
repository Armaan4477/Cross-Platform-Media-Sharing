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
            Log.e("ReceiveFileActivityPython", "Failed to retrieve OS type", e);
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
                Log.d("ReceiveFileActivityPython", "Connection established with the sender.");
                txt_waiting.setText("Receiving files from " + deviceType);
                new ReceiveFilesTask().execute();
            } else {
                Log.e("ReceiveFileActivityPython", "Failed to establish connection.");
            }
        }
    }

    private boolean initializeConnection() {
        try {
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            serverSocket = new ServerSocket(58100);
            Log.d("ReceiveFileActivityPython", "Waiting for a connection...");
            clientSocket = serverSocket.accept();
            Log.d("ReceiveFileActivityPython", "Connected to " + clientSocket.getInetAddress().getHostAddress());
            return true;
        } catch (IOException e) {
            Log.e("ReceiveFileActivityPython", "Error initializing connection", e);
            return false;
        }
    }

    @SuppressLint("StaticFieldLeak")
    private class ReceiveFilesTask extends AsyncTask<Void, Integer, Void> {
        @Override
        protected Void doInBackground(Void... voids) {
            // Close any existing connections
            try {
                if (serverSocket != null && !serverSocket.isClosed()) {
                    serverSocket.close();
                }
            } catch (IOException e) {
                Log.e("ReceiveFileActivityPython", "Error closing server socket", e);
            }
            receiveFiles();
            return null;
        }

        @Override
        protected void onProgressUpdate(Integer... values) {
            if (values.length > 0) {
                int progressValue = values[0];
                Log.d("ReceiveFilesTask", "Updating progress: " + progressValue);
                progressBar.setProgress(progressValue);
            }
            if (progressBar.getProgress() == 100) {
                txt_waiting.setText("File transfer completed");
                progressBar.setVisibility(ProgressBar.INVISIBLE);
                waitingAnimation.setVisibility(LottieAnimationView.VISIBLE);
                waitingAnimation.playAnimation();
            }
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
        protected void onPostExecute(Void result) {
            txt_waiting.setText("File transfer completed");
            progressBar.setProgress(0);
            progressBar.setVisibility(ProgressBar.INVISIBLE);
            animationView.setVisibility(LottieAnimationView.INVISIBLE);
            txt_path.setText("Files saved to: " + destinationFolder);
            txt_path.setVisibility(TextView.VISIBLE);
//            openFolder.setVisibility(Button.VISIBLE);

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
                                    ReceiveFileActivityPython.this,
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
            Log.d("ReceiveFileActivityPython", "File reception started.");
            try {
                // Load the save directory from the config file
                File configFile = new File(getFilesDir(), "config/config.json");
                saveToDirectory = loadSaveDirectoryFromConfig(configFile);
                Log.d("ReceiveFileActivityPython", "Save directory: " + saveToDirectory);

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
                        Log.e("ReceiveFileActivityPython", "Received path is a directory, removing filename from path.");
                        receivedFile = new File(destinationFolder, filePath + File.separator + fileName);
                    }

                    File parentDir = receivedFile.getParentFile();
                    if (parentDir != null && !parentDir.exists() && !parentDir.mkdirs()) {
                        Log.e("ReceiveFileActivityPython", "Failed to create directory: " + parentDir.getPath());
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
                Log.e("ReceiveFileActivityPython", "Error processing metadata for file: " + fileName, e);
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
            Log.e("ReceiveFileActivityPython", "Error receiving metadata", e);
        } catch (JSONException e) {
            Log.e("ReceiveFileActivityPython", "Error parsing metadata JSON", e);
        }
        return null; // Return null or handle accordingly if metadata reception fails
    }

    private String createFolderStructure(JSONArray metadataArray, String saveToDirectory) {
        if (metadataArray.length() == 0) {
            Log.e("ReceiveFileActivityPython", "No metadata provided for folder structure.");
            return saveToDirectory; // Return saveToDirectory if no metadata
        }

        String topLevelFolder = ""; // Variable to hold the top-level folder name

        try {
            // Extract the base folder name from the last entry if available
            JSONObject lastMetadata = metadataArray.getJSONObject(metadataArray.length() - 1);
            topLevelFolder = lastMetadata.optString("base_folder_name", "");

            if (topLevelFolder.isEmpty()) {
                Log.e("ReceiveFileActivityPython", "Base folder name not found in metadata, aborting folder creation.");
                return saveToDirectory; // Abort if no base folder name is found
            }
        } catch (JSONException e) {
            Log.e("ReceiveFileActivityPython", "Error processing metadata JSON to extract base folder name", e);
            return saveToDirectory; // Fallback if there's an error
        }

        // Construct the top-level folder path
        String topLevelFolderPath = new File(saveToDirectory, topLevelFolder).getPath();
        Log.d("ReceiveFileActivityPython", "Top-level folder path: " + topLevelFolderPath);

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
            Log.d("ReceiveFileActivityPython", "Renamed existing folder to: " + topLevelFolderPath);
        } else {
            // Create the top-level folder
            if (!topLevelDir.mkdirs()) {
                Log.e("ReceiveFileActivityPython", "Failed to create top-level folder: " + topLevelFolderPath);
                return saveToDirectory; // Fallback if folder creation fails
            }
            Log.d("ReceiveFileActivityPython", "Created top-level folder: " + topLevelFolderPath);
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
                    Log.d("ReceiveFileActivityPython", "Created folder: " + parentDir.getPath());
                }
            } catch (JSONException e) {
                Log.e("ReceiveFileActivityPython", "Error processing file info in metadata", e);
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
            Log.e("ReceiveFileActivityPython", "Error closing sockets", e);
        }
    }
}