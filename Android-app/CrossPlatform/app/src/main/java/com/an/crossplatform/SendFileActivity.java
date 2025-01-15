package com.an.crossplatform;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.Intent;
import android.icu.text.LocaleDisplayNames;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.provider.OpenableColumns;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.documentfile.provider.DocumentFile;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import android.content.ContentResolver;
import android.database.Cursor;
import android.os.Handler;
import android.os.Looper;

import java.util.concurrent.Callable;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.Arrays;
import android.widget.ProgressBar;

import com.airbnb.lottie.LottieAnimationView;
import com.an.crossplatform.AESUtils.EncryptionUtils;

public class SendFileActivity extends AppCompatActivity {

    private String receivedJson;
    private List<String> filePaths = new ArrayList<>();
    private FileAdapter fileAdapter;
    private RecyclerView recyclerView;
    private boolean metadataCreated = false;
    private String metadataFilePath = null;
    private String osType;
    private static final String TAG = "SendFileActivity";
    private boolean isFolder = false;
    private final ExecutorService executorService = Executors.newFixedThreadPool(4); // Executor for background tasks
    private final Handler mainHandler = new Handler(Looper.getMainLooper()); // For UI updates from background threads
    private String selected_device_ip;
    Socket socket = null;
    DataOutputStream dos = null;
    DataInputStream dis = null;
    private ProgressBar progressBar_send;
    private LottieAnimationView animationView;
    String base_folder_name_path;
    int progress;
    boolean metadataSent = false;
    Button selectFileButton;
    Button selectFolderButton;
    Button sendButton;
    private static final int FILE_TRANSFER_PORT = 63152;
    private static final int BUFFER_SIZE = 4096;
    boolean isEncryptionEnabled;
    private EditText passwordField;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_send);
        //forceReleasePort();

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {

                new AlertDialog.Builder(SendFileActivity.this)
                        .setTitle("Exit")
                        .setMessage("Are you sure you want to cancel the transfer?")
                        .setPositiveButton("Yes", (dialog, which) -> {
                            dialog.dismiss();
                            closeAllSockets();
                            Toast.makeText(SendFileActivity.this,  "Device Disconnected", Toast.LENGTH_SHORT).show();
                        })
                        .setNegativeButton("No", (dialog, which) -> dialog.dismiss())
                        .show();
            }
        });

        // Retrieve the JSON string from the intent
        receivedJson = getIntent().getStringExtra("receivedJson");
        selected_device_ip = getIntent().getStringExtra("selectedDeviceIP");
        progressBar_send = findViewById(R.id.progressBar_send);
        animationView = findViewById(R.id.transfer_animation);

        // set encryption from config
        isEncryptionEnabled = loadEncryptionFromConfig();
        passwordField = findViewById(R.id.editTextText4);
        if (isEncryptionEnabled) {
            passwordField.setVisibility(View.VISIBLE);
        }

        // Retrieve the OS type from the string with try catch block
        try {
            osType = new JSONObject(receivedJson).getString("os");
        } catch (Exception e) {
            FileLogger.log("SendFileActivity", "Failed to retrieve OS type", e);
        }
        FileLogger.log("SendFileActivity", "Received JSON: " + receivedJson);
        FileLogger.log("SendFileActivity", "OS Type: " + osType);
        FileLogger.log("SendFileActivity", "Selected Device IP: " + selected_device_ip);

        // Set up buttons
        selectFileButton = findViewById(R.id.btn_select_file);
        selectFolderButton = findViewById(R.id.btn_select_folder);
        sendButton = findViewById(R.id.btn_send);

        // Set up RecyclerView for displaying selected files/folder
        recyclerView = findViewById(R.id.recycler_view);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        // Initialize the adapter
        fileAdapter = new FileAdapter(filePaths);
        recyclerView.setAdapter(fileAdapter);

        // Set up button click listeners
        selectFileButton.setOnClickListener(v -> onSelectFileClicked());
        selectFolderButton.setOnClickListener(v -> onSelectFolderClicked());
        sendButton.setOnClickListener(v -> onSendClicked());
    }

    private boolean loadEncryptionFromConfig() {
        boolean encryption = false;
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
            encryption = json.optBoolean("encryption", false);
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivityPython", "Error loading saveToDirectory from config", e);
        }
        return encryption;
    }
    private final ActivityResultLauncher<Intent> filePickerLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
                if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                    // Clear previous folder selection if files are selected
                    filePaths.clear();

                    // Get selected file URIs
                    Intent data = result.getData();
                    if (data.getClipData() != null) {
                        // Multiple files selected
                        int count = data.getClipData().getItemCount();
                        for (int i = 0; i < count; i++) {
                            Uri fileUri = data.getClipData().getItemAt(i).getUri();
                            filePaths.add(fileUri.toString());
                            FileLogger.log("SendFileActivity", "File selected: " + fileUri.toString());
                        }
                    } else if (data.getData() != null) {
                        // Single file selected
                        Uri fileUri = data.getData();
                        filePaths.add(fileUri.toString());
                        FileLogger.log("SendFileActivity", "File selected: " + fileUri.toString());
                    }

                    // Refresh adapter on main thread
                    mainHandler.post(this::refreshRecyclerView);
                }
            });

    private final ActivityResultLauncher<Intent> folderPickerLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(), result -> {
                if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                    // Clear previous file selection if a folder is selected
                    filePaths.clear();

                    // Get selected folder URI
                    Uri folderUri = result.getData().getData();
                    String folderPath = folderUri.toString();
                    filePaths.add(folderPath);  // Add folder path to file list
                    FileLogger.log("SendFileActivity", "Folder selected: " + folderPath);

                    // Take persistent permissions to read the folder
                    getContentResolver().takePersistableUriPermission(folderUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);

                    // Refresh adapter on main thread
                    mainHandler.post(this::refreshRecyclerView);
                }
            });

    private void onSelectFileClicked() {
        FileLogger.log("SendFileActivity", "Select File button clicked");
        isFolder = false;

        // Launch file picker
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);  // To allow multiple file selection
        intent.addCategory(Intent.CATEGORY_OPENABLE);

        // Clear folder selection when selecting files
        filePaths.clear();

        filePickerLauncher.launch(intent);
    }

    private void onSelectFolderClicked() {
        FileLogger.log("SendFileActivity", "Select Folder button clicked");

        // Launch folder picker
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);

        // Clear file selection when selecting folder
        filePaths.clear();

        folderPickerLauncher.launch(intent);
        isFolder = true;
    }

    private void onSendClicked() {
        FileLogger.log("SendFileActivity", "Send button clicked");

        if (filePaths.isEmpty()) {
            Toast.makeText(this, "No files or folder selected", Toast.LENGTH_SHORT).show();
            return;
        }

        if (isEncryptionEnabled) {
            String password = passwordField.getText().toString();
            if (password.isEmpty()) {
                runOnUiThread( () -> {
                    Toast.makeText(SendFileActivity.this, "Please enter a password", Toast.LENGTH_LONG).show();
                });
                return;
            }
        }

        if (!metadataCreated) {
            createMetadata();
        } else {
            new Thread(new SendFileActivity.ConnectionTask(selected_device_ip)).start();
        }
    }

    private void createMetadata() {
        Callable<String> task = new Callable<String>() {
            @Override
            public String call() {
                try {
                    // Create metadata based on the selected files or folder
                    if (isFolder) {
                        return createFolderMetadata();
                    } else {
                        return createFileMetadata();
                    }
                } catch (IOException | JSONException e) {
                    FileLogger.log("SendFileActivity", "Failed to create metadata", e);
                    return null;  // Indicate failure
                }
            }
        };

        Future<String> future = executorService.submit(task);

        new Thread(() -> {
            try {
                String result = future.get();
                runOnUiThread(() -> {
                    if (result != null) {
                        metadataFilePath = result;
                        metadataCreated = true;
//                        Toast.makeText(SendFileActivityPython.this, "Metadata created: " + metadataFilePath, Toast.LENGTH_SHORT).show();
                        new Thread(new SendFileActivity.ConnectionTask(selected_device_ip)).start();
                    } else {
                        Toast.makeText(SendFileActivity.this, "Failed to create metadata", Toast.LENGTH_SHORT).show();
                    }
                });
            } catch (Exception e) {
                FileLogger.log("SendFileActivity", "Error executing metadata task", e);
            }
        }).start();
    }

    private String createFileMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();
        FileLogger.log(TAG, "Starting file metadata creation");

        File metadataDirectory =  new File(Environment.getExternalStorageDirectory(),
                "Android/media/" + getPackageName() + "/metadata/");
        ensureDirectoryExists(metadataDirectory);

        String metadataFilePath = new File(metadataDirectory, "metadata.json").getAbsolutePath();
        FileLogger.log(TAG, "Metadata file path: " + metadataFilePath);

        for (String filePath : filePaths) {
            Uri uri = Uri.parse(filePath);

            if ("content".equals(uri.getScheme())) {
                try {
                    ContentResolver contentResolver = getContentResolver();
                    if (uri != null) {
                        Cursor cursor = contentResolver.query(uri, null, null, null, null);
                        if (cursor != null && cursor.moveToFirst()) {
                            String displayName = cursor.getString(cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME));
                            long size = cursor.getLong(cursor.getColumnIndex(OpenableColumns.SIZE));

                            JSONObject fileMetadata = new JSONObject();
                            fileMetadata.put("path", displayName);
                            fileMetadata.put("size", size);
                            metadata.put(fileMetadata);

                            FileLogger.log(TAG, "Added file metadata: " + fileMetadata.toString());
                            cursor.close();
                        }
                    }
                } catch (Exception e) {
                    FileLogger.log(TAG, "Error handling content URI: " + filePath + " Exception: " + e.getMessage(), e);
                }
            } else {
                File file = new File(filePath);
                if (file.exists() && file.isFile()) {
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", file.getAbsolutePath());
                    fileMetadata.put("size", file.length());
                    metadata.put(fileMetadata);
                    FileLogger.log(TAG, "Added file metadata: " + fileMetadata.toString());
                }
            }
        }

        saveMetadataToFile(metadataFilePath, metadata);
        return metadataFilePath;
    }

    private String createFolderMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();

        // Add base folder info as first element
        JSONObject baseInfo = new JSONObject();
        baseInfo.put("base_folder_name", base_folder_name_path);
        metadata.put(baseInfo);
        FileLogger.log(TAG, "Added base folder info: " + baseInfo.toString());

        // Create metadata directory in app's external storage
        File metadataDirectory = new File(Environment.getExternalStorageDirectory(),
                "Android/media/" + getPackageName() + "/metadata/");
        if (!metadataDirectory.exists()) {
            boolean created = metadataDirectory.mkdirs();
            FileLogger.log(TAG, "Metadata directory creation result: " + created);
        }

        // Rest of metadata creation
        Uri uri = Uri.parse(filePaths.get(0));
        DocumentFile documentFile = DocumentFile.fromTreeUri(this, uri);
        if (documentFile != null) {
            addFolderMetadataFromDocumentFile(documentFile, metadata, "");
        }

        // Save metadata
        String metadataFilePath = new File(metadataDirectory, "metadata.json").getAbsolutePath();
        saveMetadataToFile(metadataFilePath, metadata);
        FileLogger.log(TAG, "Metadata saved to: " + metadataFilePath);

        return metadataFilePath;
    }

    private void addFolderMetadataFromDocumentFile(DocumentFile folder, JSONArray metadata, String relativePath) throws JSONException {
        String folderName = folder.getName();
        // Don't append folderName if relativePath is empty
        String currentRelativePath = relativePath.isEmpty() ? folderName : relativePath + "/" + folderName;

        // Add folder entry
        JSONObject folderMetadata = new JSONObject();
        folderMetadata.put("path", currentRelativePath + "/");
        folderMetadata.put("size", 0);
        metadata.put(folderMetadata);

        // Process contents
        for (DocumentFile file : folder.listFiles()) {
            if (file.isDirectory()) {
                addFolderMetadataFromDocumentFile(file, metadata, currentRelativePath);
            } else if (file.isFile()) {
                JSONObject fileMetadata = new JSONObject();
                fileMetadata.put("path", currentRelativePath + "/" + file.getName());
                fileMetadata.put("size", file.length());
                metadata.put(fileMetadata);
            }
        }
    }

    private void addFolderMetadata(File folder, JSONArray metadata, String relativePath) throws IOException, JSONException {
        String folderName = folder.getName();
        String currentRelativePath = relativePath.isEmpty() ? folderName : relativePath + "/" + folderName;

        // Add metadata for the current folder
        JSONObject folderMetadata = new JSONObject();
        folderMetadata.put("path", currentRelativePath + "/");
        folderMetadata.put("size", 0); // Directories have size 0
        metadata.put(folderMetadata);
        FileLogger.log(TAG, "Added folder metadata: " + folderMetadata.toString());

        // Recursively process contents
        File[] files = folder.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    addFolderMetadata(file, metadata, currentRelativePath);
                } else if (file.isFile()) {
                    String fileRelativePath = currentRelativePath + "/" + file.getName();
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", fileRelativePath);
                    fileMetadata.put("size", file.length());
                    metadata.put(fileMetadata);
                    FileLogger.log(TAG, "Added file metadata: " + fileMetadata.toString());
                }
            }
        } else {
            FileLogger.log(TAG, "Could not list files for directory: " + folder.getAbsolutePath());
        }
    }

    private String getPathFromUri(Uri uri) {
        String path = uri.getPath();
        if (path != null) {
            String[] pathSegments = path.split("/");
            if (pathSegments.length > 2 && "document".equals(pathSegments[0]) && pathSegments[1].startsWith("primary:")) {
                return String.join("/", Arrays.copyOfRange(pathSegments, 2, pathSegments.length));
            }
        }
        return path;
    }

    private void ensureDirectoryExists(File directory) {
        if (!directory.exists()) {
            FileLogger.log(TAG, "Directory does not exist, attempting to create: " + directory.getAbsolutePath());
            if (directory.mkdirs()) {
                FileLogger.log(TAG, "Directory created: " + directory.getAbsolutePath());
            } else {
                FileLogger.log(TAG, "Failed to create directory: " + directory.getAbsolutePath());
            }
        } else {
            FileLogger.log(TAG, "Directory already exists: " + directory.getAbsolutePath());
        }
    }

    private void saveMetadataToFile(String filePath, JSONArray metadata) throws IOException {
        FileLogger.log(TAG, "Saving metadata to file: " + filePath);
        try (FileWriter fileWriter = new FileWriter(filePath)) {
            fileWriter.write(metadata.toString());
            fileWriter.flush();
            FileLogger.log(TAG, "Metadata saved successfully");
        } catch (IOException e) {
            FileLogger.log(TAG, "Error saving metadata to file: " + e.getMessage(), e);
            throw e;
        }
    }

    private void refreshRecyclerView() {
        fileAdapter.notifyDataSetChanged();
    }

    private class ConnectionTask implements Runnable {
        private final String ip;
        private final AtomicInteger pendingTransfers;

        ConnectionTask(String ip) {
            this.ip = ip;
            this.pendingTransfers = new AtomicInteger(getTotalFileCount());
        }

        private int getTotalFileCount() {
            int count = 0;
            for (String filePath : filePaths) {
                if (isFolder) {
                    count += countFilesInFolder(filePath); // Count files in folder
                } else {
                    count++;
                }
            }
            FileLogger.log("SendFileActivity", "Total files to send: " + count);
            return count + 1;
        }

        private int countFilesInFolder(String folderPath) {
            Uri folderUri = Uri.parse(folderPath);
            DocumentFile folderDocument = DocumentFile.fromTreeUri(SendFileActivity.this, folderUri);

            if (folderDocument != null && folderDocument.isDirectory()) {
                return countFilesRecursively(folderDocument);
            }
            return 0;
        }

        private int countFilesRecursively(DocumentFile directory) {
            int fileCount = 0;
            for (DocumentFile file : directory.listFiles()) {
                if (file.isDirectory()) {
                    fileCount += countFilesRecursively(file); // Add files from subdirectories
                } else {
                    fileCount++;
                }
            }
            return fileCount;
        }

        @Override
        public void run() {
            try {
                socket = new Socket();
                socket.setReuseAddress(true); // Add this to prevent port binding issues
                FileLogger.log("SendFileActivity", "Attempting connection to " + ip + ":" + FILE_TRANSFER_PORT);
                socket.connect(new InetSocketAddress(ip, FILE_TRANSFER_PORT), 10000);
                FileLogger.log("SendFileActivity", "Connected successfully to port " + FILE_TRANSFER_PORT);

                if (!socket.isConnected()) {
                    throw new IOException("Failed to connect to port " + FILE_TRANSFER_PORT);
                }

                // Send files/folders if connection is successful
                for (String filePath : filePaths) {
                    if (isFolder) {
                        sendFolder(filePath);
                    } else {
                        if (!metadataSent) {
                            sendFile(metadataFilePath, null, false);
                            metadataSent = true;
                        }
                        sendFile(filePath, null, isEncryptionEnabled);
                    }
                }
            } catch (IOException e) {
                FileLogger.log("SendFileActivity", "Connection failed on port " + FILE_TRANSFER_PORT, e);
                runOnUiThread(() ->
                        Toast.makeText(SendFileActivity.this,
                                "Connection Failed on port " + FILE_TRANSFER_PORT,
                                Toast.LENGTH_SHORT).show()
                );
                closeSocket();
            }
        }

        private void onTransferComplete() {
            int remainingTransfers = pendingTransfers.decrementAndGet();
            FileLogger.log("SendFileActivity", "Files remaining: " + remainingTransfers); // Debugging line

            if (remainingTransfers == 0) {
                sendHaltEncryptionSignal(); // Send halt signal once all transfers complete
            }
        }

        private void sendHaltEncryptionSignal() {
            try {
                DataOutputStream dos = new DataOutputStream(socket.getOutputStream());
                String haltEncryptionSignal = "encyp: h";
                dos.write(haltEncryptionSignal.getBytes(StandardCharsets.UTF_8));
                dos.flush();
                FileLogger.log("SendFileActivity", "Sent halt encryption signal: " + haltEncryptionSignal);
                runOnUiThread(() -> {
                    if (progressBar_send.getProgress() == 100) {
                        progressBar_send.setProgress(0);
                        progressBar_send.setVisibility(ProgressBar.INVISIBLE);
                        animationView.setVisibility(LottieAnimationView.INVISIBLE);
                        selectFileButton.setEnabled(false);
                        selectFolderButton.setEnabled(false);
                        sendButton.setEnabled(false);
                        //Toast.makeText(SendFileActivity.this, "Sending Completed", Toast.LENGTH_SHORT).show();
                        // Launch TransferCompleteActivity
                        Intent intent = new Intent(SendFileActivity.this, TransferCompleteActivity.class);
                        startActivity(intent);
                        finish(); // Close current activity
                    }
                });
            } catch (IOException e) {
                FileLogger.log("SendFileActivity", "Error sending halt encryption signal", e);
            }
        }

        private void sendFile(String filePath, String relativePath) {
            // Default constructor to send files without encryption
            boolean encryptedTransfer=false;
            sendFile(filePath, relativePath, encryptedTransfer);
        }

        private void sendFile(String filePath, String relativePath, boolean encryptedTransfer) {
            if (filePath == null) {
                FileLogger.log("SendFileActivity", "File path is null");
                return;
            }

            final String password = passwordField.getText().toString();

            // Create a CountDownLatch for sequential file transfers
            CountDownLatch latch = new CountDownLatch(1);

            executorService.execute(() -> {
                try {
                    InputStream inputStream;
                    String finalRelativePath;
                    String originalFileName = "encryptedfile";

                    // Initialize finalRelativePath based on relativePath or fallback to filePath
                    if (relativePath == null || relativePath.isEmpty()) {
                        finalRelativePath = new File(filePath).getName();
                    } else {
                        finalRelativePath = relativePath;
                    }
                    FileLogger.log("SendFileActivity", "Initial relative path: " + finalRelativePath);

                    // Check if the filePath is a content URI
                    Uri fileUri = Uri.parse(filePath);

                    if (filePath.startsWith("content://")) {
                        // Use ContentResolver to open the file from the URI
                        ContentResolver contentResolver = getContentResolver();
                        inputStream = contentResolver.openInputStream(fileUri);

                        // Get the file name from content URI
                        Cursor cursor = contentResolver.query(fileUri, null, null, null, null);
                        if (cursor != null && cursor.moveToFirst()) {
                            // Retrieve the display name (actual file name)
                            int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                            String contentUriFileName = cursor.getString(nameIndex);
                            originalFileName = contentUriFileName;
                            cursor.close();

                            // Use contentUriFileName only if relativePath was null or empty
                            if (relativePath == null || relativePath.isEmpty()) {
                                finalRelativePath = contentUriFileName;
                            }
                        } else if (relativePath == null || relativePath.isEmpty()) {
                            // Fallback to file name from URI path if cursor fails
                            finalRelativePath = new File(fileUri.getPath()).getName();
                            originalFileName = finalRelativePath;
                        }
                    } else {
                        // If it's a file path, open it directly and extract the file name
                        File file = new File(fileUri.getPath());
                        originalFileName = file.getName();
                        inputStream = new FileInputStream(file);

                        // Use the file name only if relativePath was null or empty
                        if (relativePath == null || relativePath.isEmpty()) {
                            finalRelativePath = file.getName();
                        }
                    }

                    InputStream finalInputStream = inputStream;
                    String finalPathToSend = finalRelativePath;

                    runOnUiThread(() -> {
                        progressBar_send.setMax(100);
                        progressBar_send.setProgress(0);
                        progressBar_send.setVisibility(ProgressBar.VISIBLE);
                        animationView.setVisibility(LottieAnimationView.VISIBLE);
                        animationView.playAnimation();
                    });

                    try {
                        DataOutputStream dos = new DataOutputStream(socket.getOutputStream());
                        File encryptedFile = null;

                        // Determine the encryption flag
                        String encryptionFlag = encryptedTransfer ? "encyp: t" : "encyp: f";
                        dos.write(encryptionFlag.getBytes(StandardCharsets.UTF_8));
                        dos.flush();
                        FileLogger.log("SendFileActivity", "Sent encryption flag: " + encryptionFlag);


                        if (encryptedTransfer) {
                            try {
                                // Encrypt the file and create a new encrypted file with the .crypt extension
                                encryptedFile = new File(getCacheDir(),originalFileName + ".crypt");
                                EncryptionUtils.encryptFile(password, (FileInputStream) inputStream, encryptedFile);

                                // Update finalInputStream and finalPathToSend with encrypted file details
                                finalInputStream = new FileInputStream(encryptedFile);

                                // Add ".crypt" to relative path
                                finalPathToSend += ".crypt";

                                FileLogger.log("SendFileActivity", "Encrypted file to send: " + encryptedFile.getAbsolutePath());
                            } catch (Exception e) {
                                FileLogger.log("SendFileActivity", "Error encrypting file", e);
                                return; // Stop further processing if encryption fails
                            }
                        }
                        // Send the relative path size and the path
                        byte[] relativePathBytes = finalPathToSend.getBytes(StandardCharsets.UTF_8);
                        long relativePathSize = relativePathBytes.length;

                        ByteBuffer pathSizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                        pathSizeBuffer.putLong(relativePathSize);
                        dos.write(pathSizeBuffer.array());
                        dos.flush();

                        dos.write(relativePathBytes);
                        dos.flush();

                        // Send the file size
                        ByteBuffer sizeBuffer = ByteBuffer.allocate(Long.BYTES).order(ByteOrder.LITTLE_ENDIAN);
                        long fileSize = finalInputStream.available();
                        sizeBuffer.putLong(fileSize);
                        dos.write(sizeBuffer.array());
                        dos.flush();

                        // Send the file data
                        byte[] buffer = new byte[BUFFER_SIZE];
                        long sentSize = 0;

                        while (sentSize < fileSize) {
                            int bytesRead = finalInputStream.read(buffer);
                            if (bytesRead == -1) break;
                            dos.write(buffer, 0, bytesRead);
                            sentSize += bytesRead;
                            int progress = (int) (sentSize * 100 / fileSize);
                            runOnUiThread(() -> progressBar_send.setProgress(progress));
                        }
                        dos.flush();
                        finalInputStream.close();

                        // Check if the transfer was encrypted and delete the encrypted file
                        if (encryptedTransfer) {
                            encryptedFile.delete();
                        }
                    } catch (IOException e) {
                        FileLogger.log("SendFileActivity", "Error sending file", e);
                    }
                } catch (IOException e) {
                    FileLogger.log("SendFileActivity", "Error initializing connection", e);
                } finally {
                    onTransferComplete(); // Call after each file transfer completes
                    // Count down the latch to allow the next file to send
                    latch.countDown();
                }
            });

            try {
                // Wait for the current file transfer to complete
                latch.await();
            } catch (InterruptedException e) {
                FileLogger.log("SendFileActivity", "Interrupted while waiting for file transfer to complete", e);
            }
        }

        private void sendFolder(String folderPath) {
            // Convert the String folderPath to a Uri
            Uri folderUri = Uri.parse(folderPath);  // Assuming folderPath is a content URI string

            executorService.execute(() -> {
                try {
                    // Create a DocumentFile from the tree URI to traverse the folder
                    DocumentFile folderDocument = DocumentFile.fromTreeUri(SendFileActivity.this, folderUri);

                    if (folderDocument == null) {
                        FileLogger.log("SendFileActivity", "Error: DocumentFile is null. Invalid URI or permission issue.");
                        return;
                    }

                    // Send the metadata file first
                    if (metadataFilePath != null) {
                        sendFile(metadataFilePath, "", false);
                        metadataSent = true;
                    } else {
                        FileLogger.log("SendFileActivity", "Metadata file path is null. Metadata file not sent.");
                        return;
                    }

                    // Start recursion with empty relative path (top-level folder will be included)
                    sendDocumentFile(folderDocument, "");
                } catch (Exception e) {
                    FileLogger.log("SendFileActivity", "Error sending folder", e);
                }
            });
        }

        // Modified recursive method to send the contents of a DocumentFile (folder or file)
        private void sendDocumentFile(DocumentFile documentFile, String relativePath) {
            if (documentFile.isDirectory()) {
                String folderName = documentFile.getName();
                String currentRelativePath = relativePath.isEmpty() ? folderName : relativePath + "/" + folderName;

                // Recursively send contents
                for (DocumentFile file : documentFile.listFiles()) {
                    sendDocumentFile(file, currentRelativePath);
                }
            } else if (documentFile.isFile()) {
                String fileRelativePath = relativePath.isEmpty() ? documentFile.getName() : relativePath + "/" + documentFile.getName();
                FileLogger.log("SendFileActivity", "Sending file: " + fileRelativePath);

                try {
                    InputStream inputStream = getContentResolver().openInputStream(documentFile.getUri());
                    if (inputStream != null) {
                        sendFile(documentFile.getUri().toString(), fileRelativePath, isEncryptionEnabled);
                        inputStream.close();
                    }
                } catch (IOException e) {
                    FileLogger.log("SendFileActivity", "Error sending file: " + fileRelativePath, e);
                }
            }
        }

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
    private void closeSocket() {
        try {
            if (socket != null && !socket.isClosed()) {
                socket.close();
                FileLogger.log("SendFileActivity", "Socket closed on port " + FILE_TRANSFER_PORT);
            }
        } catch (IOException e) {
            FileLogger.log("SendFileActivity", "Error closing socket on port " + FILE_TRANSFER_PORT, e);
        }
    }

    private void closeAllSockets() {
        try {
            // Close socket-related resources
            if (dos != null) {
                dos.close();
                FileLogger.log("SendFileActivity", "DataOutputStream closed");
            }
            if (dis != null) {
                dis.close();
                FileLogger.log("SendFileActivity", "DataInputStream closed");
            }
            if (socket != null && !socket.isClosed()) {
                socket.close();
                FileLogger.log("SendFileActivity", "Socket closed");
            }

            // Shutdown executor
            executorService.shutdown();
            FileLogger.log("SendFileActivity", "ExecutorService shutdown");

            finish(); // Close the activity
        } catch (IOException e) {
            FileLogger.log("SendFileActivity", "Error closing sockets", e);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeAllSockets();
    }
}
