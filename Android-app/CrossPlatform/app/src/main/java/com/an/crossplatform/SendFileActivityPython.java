package com.an.crossplatform;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Log;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.Toast;
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

import com.airbnb.lottie.LottieAnimationView;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.Arrays;
import java.util.concurrent.Future;

public class SendFileActivityPython extends AppCompatActivity {

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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_send);

        // Retrieve the JSON string from the intent
        receivedJson = getIntent().getStringExtra("receivedJson");
        selected_device_ip = getIntent().getStringExtra("selectedDeviceIP");
        progressBar_send = findViewById(R.id.progressBar_send);
        animationView = findViewById(R.id.transfer_animation);

        // Retrieve the OS type from the string with try catch block
        try {
            osType = new JSONObject(receivedJson).getString("os");
        } catch (Exception e) {
            Log.e("SendFileActivity", "Failed to retrieve OS type", e);
        }
        Log.d("SendFileActivity", "Received JSON: " + receivedJson);
        Log.d("SendFileActivity", "OS Type: " + osType);
        Log.d("SendFileActivity", "Selected Device IP: " + selected_device_ip);

        // Set up buttons
        Button selectFileButton = findViewById(R.id.btn_select_file);
        Button selectFolderButton = findViewById(R.id.btn_select_folder);
        Button sendButton = findViewById(R.id.btn_send);

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
                            Log.d("SendFileActivity", "File selected: " + fileUri.toString());
                        }
                    } else if (data.getData() != null) {
                        // Single file selected
                        Uri fileUri = data.getData();
                        filePaths.add(fileUri.toString());
                        Log.d("SendFileActivity", "File selected: " + fileUri.toString());
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
                    Log.d("SendFileActivity", "Folder selected: " + folderPath);

                    // Take persistent permissions to read the folder
                    getContentResolver().takePersistableUriPermission(folderUri, Intent.FLAG_GRANT_READ_URI_PERMISSION);

                    // Refresh adapter on main thread
                    mainHandler.post(this::refreshRecyclerView);
                }
            });

    private void onSelectFileClicked() {
        Log.d("SendFileActivity", "Select File button clicked");

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
        Log.d("SendFileActivity", "Select Folder button clicked");

        // Launch folder picker
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);

        // Clear file selection when selecting folder
        filePaths.clear();

        folderPickerLauncher.launch(intent);
        isFolder = true;
    }

    private void onSendClicked() {
        Log.d("SendFileActivity", "Send button clicked");

        if (filePaths.isEmpty()) {
            Toast.makeText(this, "No files or folder selected", Toast.LENGTH_SHORT).show();
            return;
        }

        if (!metadataCreated) {
            createMetadata();
        } else {
            new Thread(new ConnectionTask(selected_device_ip)).start();
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
                    Log.e("SendFileActivity", "Failed to create metadata", e);
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
                        Toast.makeText(SendFileActivityPython.this, "Metadata created: " + metadataFilePath, Toast.LENGTH_SHORT).show();
                        new Thread(new ConnectionTask(selected_device_ip)).start();
                    } else {
                        Toast.makeText(SendFileActivityPython.this, "Failed to create metadata", Toast.LENGTH_SHORT).show();
                    }
                });
            } catch (Exception e) {
                Log.e("SendFileActivity", "Error executing metadata task", e);
            }
        }).start();
    }

    private String createFileMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();
        Log.d(TAG, "Starting file metadata creation");

        File metadataDirectory = new File(getApplicationContext().getFilesDir(), "metadata");
        ensureDirectoryExists(metadataDirectory);

        String metadataFilePath = new File(metadataDirectory, "metadata.json").getAbsolutePath();
        Log.d(TAG, "Metadata file path: " + metadataFilePath);

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

                            Log.d(TAG, "Added file metadata: " + fileMetadata.toString());
                            cursor.close();
                        }
                    }
                } catch (Exception e) {
                    Log.e(TAG, "Error handling content URI: " + filePath + " Exception: " + e.getMessage(), e);
                }
            } else {
                File file = new File(filePath);
                if (file.exists() && file.isFile()) {
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", file.getAbsolutePath());
                    fileMetadata.put("size", file.length());
                    metadata.put(fileMetadata);
                    Log.d(TAG, "Added file metadata: " + fileMetadata.toString());
                }
            }
        }

        saveMetadataToFile(metadataFilePath, metadata);
        return metadataFilePath;
    }

    private String createFolderMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();
        Log.d(TAG, "Starting folder metadata creation");

        File metadataDirectory = new File(getApplicationContext().getFilesDir(), "metadata");
        Log.d(TAG, "Metadata directory path: " + metadataDirectory.getAbsolutePath());
        ensureDirectoryExists(metadataDirectory);

        String metadataFilePath = new File(metadataDirectory, "metadata.json").getAbsolutePath();
        Log.d(TAG, "Metadata file path: " + metadataFilePath);

        for (String filePath : filePaths) {
            Uri uri = Uri.parse(filePath);

            if ("content".equals(uri.getScheme())) {
                DocumentFile documentFile = DocumentFile.fromTreeUri(this, uri);
                if (documentFile != null) {
                    if (documentFile.isDirectory()) {
                        Log.d(TAG, "Processing directory from URI: " + filePath);
                        addFolderMetadataFromDocumentFile(documentFile, metadata, "");
                    } else if (documentFile.isFile()) {
                        JSONObject fileMetadata = new JSONObject();
                        String path = getPathFromUri(uri);
                        fileMetadata.put("path", path);
                        fileMetadata.put("size", documentFile.length());
                        metadata.put(fileMetadata);
                        Log.d(TAG, "Added file metadata: " + fileMetadata.toString());
                    } else {
                        Log.e(TAG, "Unsupported content URI: " + filePath);
                    }
                } else {
                    Log.e(TAG, "Could not resolve content URI: " + filePath);
                }
            } else {
                File file = new File(filePath);
                if (file.isDirectory()) {
                    Log.d(TAG, "Processing directory: " + filePath);
                    addFolderMetadata(file, metadata, "");
                } else {
                    Log.e(TAG, "File not found or not valid: " + filePath);
                }
            }
        }

        JSONObject base_folder_name = new JSONObject();
        base_folder_name_path = filePaths.get(0);
        if (base_folder_name_path.startsWith("content://")) {
            DocumentFile baseFolderDocument = DocumentFile.fromTreeUri(this, Uri.parse(base_folder_name_path));
            if (baseFolderDocument != null) {
                base_folder_name_path = baseFolderDocument.getName();
            }
        } else {
            File baseFolder = new File(base_folder_name_path);
            if (baseFolder.exists()) {
                base_folder_name_path = baseFolder.getName();
            }
        }
        base_folder_name.put("base_folder_name", base_folder_name_path);
        base_folder_name.put("path", ".delete");
        base_folder_name.put("size", 0);
        metadata.put(base_folder_name);

        Log.d(TAG, "Metadata before saving: " + metadata.toString());

        try {
            saveMetadataToFile(metadataFilePath, metadata);
            metadataCreated = true;
        } catch (IOException e) {
            Log.e(TAG, "Failed to create metadata: " + e.getMessage(), e);
            metadataCreated = false;
        }

        return metadataFilePath;
    }

    private void addFolderMetadataFromDocumentFile(DocumentFile folder, JSONArray metadata, String basePath) throws JSONException {
        Log.d(TAG, "Traversing DocumentFile folder: " + folder.getUri().toString());
        DocumentFile[] files = folder.listFiles();
        if (files != null) {
            for (DocumentFile file : files) {
                JSONObject fileMetadata = new JSONObject();
                String path = basePath + file.getName();
                fileMetadata.put("path", path + (file.isDirectory() ? "/" : ""));
                fileMetadata.put("size", file.isDirectory() ? 0 : file.length());
                metadata.put(fileMetadata);
                Log.d(TAG, "Added metadata: " + fileMetadata.toString());

                if (file.isDirectory()) {
                    addFolderMetadataFromDocumentFile(file, metadata, path + "/");
                }
            }
        } else {
            Log.e(TAG, "Could not list files for directory: " + folder.getUri().toString());
        }
    }

    private void addFolderMetadata(File folder, JSONArray metadata, String basePath) throws IOException, JSONException {
        Log.d(TAG, "Traversing folder: " + folder.getAbsolutePath());
        File[] files = folder.listFiles();
        if (files != null) {
            for (File file : files) {
                JSONObject fileMetadata = new JSONObject();
                String relativePath = basePath + file.getName();
                fileMetadata.put("path", relativePath + (file.isDirectory() ? "/" : ""));
                fileMetadata.put("size", file.isDirectory() ? 0 : file.length());
                metadata.put(fileMetadata);
                Log.d(TAG, "Added metadata: " + fileMetadata.toString());

                if (file.isDirectory()) {
                    addFolderMetadata(file, metadata, relativePath + "/");
                }
            }
        } else {
            Log.e(TAG, "Could not list files for directory: " + folder.getAbsolutePath());
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
            Log.d(TAG, "Directory does not exist, attempting to create: " + directory.getAbsolutePath());
            if (directory.mkdirs()) {
                Log.d(TAG, "Directory created: " + directory.getAbsolutePath());
            } else {
                Log.e(TAG, "Failed to create directory: " + directory.getAbsolutePath());
            }
        } else {
            Log.d(TAG, "Directory already exists: " + directory.getAbsolutePath());
        }
    }

    private void saveMetadataToFile(String filePath, JSONArray metadata) throws IOException {
        Log.d(TAG, "Saving metadata to file: " + filePath);
        try (FileWriter fileWriter = new FileWriter(filePath)) {
            fileWriter.write(metadata.toString());
            fileWriter.flush();
            Log.d(TAG, "Metadata saved successfully");
        } catch (IOException e) {
            Log.e(TAG, "Error saving metadata to file: " + e.getMessage(), e);
            throw e;
        }
    }

    private void refreshRecyclerView() {
        fileAdapter.notifyDataSetChanged();
    }

    private class ConnectionTask implements Runnable {
        private final String ip;

        ConnectionTask(String ip) {
            this.ip = ip;
        }

        @Override
        public void run() {
            // Initialize connection
            try {
                socket = new Socket();
                socket.connect(new InetSocketAddress(ip, 58000), 10000);
                Log.d("SendFileActivity", "Socket connected: " + socket.isConnected());
            } catch (IOException e) {
                Log.e("SendFileActivity", "Failed to connect to server", e);
                runOnUiThread(() ->
                        Toast.makeText(SendFileActivityPython.this, "Connection Failed", Toast.LENGTH_SHORT).show()
                );
                return;
            }

            // Send files/folders if connection is successful
            for (String filePath : filePaths) {
                if (isFolder) {
                    sendFolder(filePath);
                } else {
                    sendFile(filePath, null);
                }
            }
        }
    }

    private void sendFile(String filePath, String relativePath) {
        boolean encryptedTransfer = false;  // Set to true if you want to encrypt the file before sending

        if (filePath == null) {
            Log.e("SendFileActivity", "File path is null");
            return;
        }

        executorService.execute(() -> {
            try {
                InputStream inputStream;
                String finalRelativePath;  // Declare finalRelativePath here

                // Check if relativePath is null and initialize it based on the filePath
                if (relativePath == null) {
                    finalRelativePath = new File(filePath).getName();
                } else {
                    finalRelativePath = relativePath;
                }

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
                        finalRelativePath = cursor.getString(nameIndex);
                        cursor.close();
                    } else {
                        // Fallback to using the last segment of the URI path
                        finalRelativePath = new File(fileUri.getPath()).getName();
                    }
                } else {
                    // If it's a file path, open it directly and extract the file name
                    File file = new File(fileUri.getPath());
                    inputStream = new FileInputStream(file);
                    finalRelativePath = file.getName();  // Get the name of the file
                }

                // Make final variables to use inside AsyncTask
                final InputStream finalInputStream = inputStream;
                final String finalPathToSend = finalRelativePath;
                final long fileSize = finalInputStream.available();  // Get file size from the InputStream

                runOnUiThread(() -> {
                    progressBar_send.setMax(100);
                    progressBar_send.setProgress(0);
                    progressBar_send.setVisibility(ProgressBar.VISIBLE);
                    animationView.setVisibility(LottieAnimationView.VISIBLE);
                    animationView.playAnimation();
                });

                try {
                    DataOutputStream dos = new DataOutputStream(socket.getOutputStream());

                    // Determine the encryption flag
                    String encryptionFlag = encryptedTransfer ? "encyp: t" : "encyp: f";
                    dos.write(encryptionFlag.getBytes(StandardCharsets.UTF_8));
                    dos.flush();
                    Log.d("SendFileActivity", "Sent encryption flag: " + encryptionFlag);

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
                    sizeBuffer.putLong(fileSize);
                    dos.write(sizeBuffer.array());
                    dos.flush();

                    // Send the file data
                    byte[] buffer = new byte[4096];
                    long sentSize = 0;

                    while (sentSize < fileSize) {
                        int bytesRead = finalInputStream.read(buffer);  // Use finalInputStream here
                        if (bytesRead == -1) break;
                        dos.write(buffer, 0, bytesRead);
                        sentSize += bytesRead;
                        int progress = (int) (sentSize * 100 / fileSize);
                        runOnUiThread(() -> {
                            progressBar_send.setProgress(progress);
                            if(progress == 100) {

                                progressBar_send.setProgress(0);
                                progressBar_send.setVisibility(ProgressBar.INVISIBLE);
                                animationView.setVisibility(LottieAnimationView.INVISIBLE);
                                Toast.makeText(SendFileActivityPython.this, "Sending Completed", Toast.LENGTH_SHORT).show();
                            }
                        });
                    }
                    dos.flush();

                    finalInputStream.close();
                } catch (IOException e) {
                    Log.e("SendFileActivity", "Error sending file", e);
                }
            } catch (IOException e) {
                Log.e("SendFileActivity", "Error initializing connection", e);
            }
        });
    }

    private void sendFolder(String folderPath) {
        boolean encryptionFlag = false;  // Set to true if you want to encrypt the files before sending

        // Convert the String folderPath to a Uri
        Uri folderUri = Uri.parse(folderPath);  // Assuming folderPath is a content URI string

        // Ensure metadataFilePath is set and not null
        if (metadataFilePath != null) {
            // Send the metadata file first
            sendFile(metadataFilePath, "");
        } else {
            Log.e("SendFileActivity", "Metadata file path is null. Metadata file not sent.");
            return;
        }

        executorService.execute(() -> {
            try {
                // Create a DocumentFile from the tree URI to traverse the folder
                DocumentFile folderDocument = DocumentFile.fromTreeUri(this, folderUri);

                if (folderDocument == null) {
                    Log.e("SendFileActivity", "Error: DocumentFile is null. Invalid URI or permission issue.");
                    return;
                }

                // Check if the DocumentFile is a directory (folder)
                if (folderDocument.isDirectory()) {
                    // Send the folder contents recursively
                    sendDocumentFile(folderDocument, "", encryptionFlag);
                } else {
                    Log.e("SendFileActivity", "Error: The provided URI is not a folder.");
                }
            } catch (Exception e) {
                Log.e("SendFileActivity", "Error sending folder", e);
            }
        });
    }

    // Recursive method to send the contents of a DocumentFile (folder or file)
    private void sendDocumentFile(DocumentFile documentFile, String parentPath, boolean encryptionFlag) {
        if (documentFile.isDirectory()) {
            // Send the directory creation command
            String directoryPath = parentPath + documentFile.getName() + "/";
            Log.d("SendFileActivity", "Directory creation needed for: " + directoryPath);

            // Recursively send the contents of the directory
            for (DocumentFile file : documentFile.listFiles()) {
                sendDocumentFile(file, directoryPath, encryptionFlag);
            }
        } else if (documentFile.isFile()) {
            // It's a file, send the file
            String relativeFilePath = parentPath + documentFile.getName();
            Log.d("SendFileActivity", "Sending file: " + relativeFilePath);

            try {
                InputStream inputStream = getContentResolver().openInputStream(documentFile.getUri());
                if (inputStream != null) {
                    // Send the file data via your existing send logic
                    sendFile(documentFile.getUri().toString(), relativeFilePath);
                    inputStream.close();
                }
            } catch (IOException e) {
                Log.e("SendFileActivity", "Error sending file: " + relativeFilePath, e);
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Close the socket connection when the activity is destroyed
        try {
            if (socket != null) {
                socket.close();
                Log.d("SendFileActivity", "Socket closed");
            }
        } catch (IOException e) {
            Log.e("SendFileActivity", "Error closing socket", e);
        }
        executorService.shutdown();  // Clean up background threads
    }

    @Override
    public void onBackPressed() {
        super.onBackPressed();
        // Close sockets on activity destruction
        try {
            if (socket != null) {
                socket.close();
                Log.d("SendFileActivity", "Socket closed");
            }
        } catch (IOException e) {
            Log.e("SendFileActivity", "Error closing socket", e);
        }
    }
}
