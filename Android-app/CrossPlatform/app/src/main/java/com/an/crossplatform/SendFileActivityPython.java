package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
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
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import android.content.ContentResolver;
import android.net.Uri;
import android.content.Context;
import android.database.Cursor;
import android.provider.DocumentsContract;
import android.provider.MediaStore;

public class SendFileActivityPython extends AppCompatActivity {

    private String receivedJson;
    private List<String> filePaths = new ArrayList<>();
    private FileAdapter fileAdapter;
    private RecyclerView recyclerView;
    private boolean metadataCreated = false;
    private String metadataFilePath = null;
    private String osType;
    private static final String TAG = "SendFileActivity";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_send);

        // Retrieve the JSON string from the intent
        receivedJson = getIntent().getStringExtra("receivedJson");
        // Retrieve the OS type from the string with try catch block
        try {
            osType = new JSONObject(receivedJson).getString("os");
        } catch (Exception e) {
            Log.e("SendFileActivity", "Failed to retrieve OS type", e);
        }
        Log.d("SendFileActivity", "Received JSON: " + receivedJson);
        Log.d("SendFileActivity", "OS Type: " + osType);

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

                    // Refresh adapter
                    refreshRecyclerView();
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

                    // Refresh adapter
                    refreshRecyclerView();
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
    }

    private void onSendClicked() {
        Log.d("SendFileActivity", "Send button clicked");

        if (!filePaths.isEmpty()) {
            try {
                // Create metadata based on the selected files or folder
                metadataFilePath = createMetadata();
                Toast.makeText(this, "Metadata created: " + metadataFilePath, Toast.LENGTH_SHORT).show();

                // Log and send the selected file/folder paths
                Log.d("SendFileActivity", "Files to send: " + filePaths);
            } catch (IOException | JSONException e) {
                Log.e("SendFileActivity", "Failed to create metadata", e);
                Toast.makeText(this, "Failed to create metadata", Toast.LENGTH_SHORT).show();
            }
        } else {
            Toast.makeText(this, "No files or folder selected", Toast.LENGTH_SHORT).show();
        }

        Log.d("SendFileActivity", "Metadata created: " + metadataFilePath);
        // Log the contents of the metadata file
        if (metadataCreated) {
            try {
                Log.d("SendFileActivity", "Metadata file contents: " + readMetadataFile(metadataFilePath));
            } catch (IOException e) {
                Log.e("SendFileActivity", "Failed to read metadata file", e);
            }
        }
    }

    private String createMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();
        Log.d(TAG, "Starting metadata creation");

        // Determine the target directory for metadata files
        File metadataDirectory = new File(getApplicationContext().getFilesDir(), "metadata");
        Log.d(TAG, "Metadata directory path: " + metadataDirectory.getAbsolutePath());
        ensureDirectoryExists(metadataDirectory);

        String metadataFilePath = new File(metadataDirectory, "metadata.json").getAbsolutePath();
        Log.d(TAG, "Metadata file path: " + metadataFilePath);

        // Process the file paths
        for (String filePath : filePaths) {
            Uri uri = Uri.parse(filePath);

            if (uri.getScheme().equals("content")) {
                // Handle content URIs using DocumentFile
                DocumentFile documentFile = DocumentFile.fromTreeUri(this, uri);
                if (documentFile != null && documentFile.isDirectory()) {
                    Log.d(TAG, "Processing directory from URI: " + filePath);
                    addFolderMetadataFromDocumentFile(documentFile, metadata);
                } else if (documentFile != null && documentFile.isFile()) {
                    // Handle individual file
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", documentFile.getName());
                    fileMetadata.put("size", documentFile.length());
                    metadata.put(fileMetadata);
                    Log.d(TAG, "Added file metadata: " + fileMetadata.toString());
                }
            } else {
                // Handle file system paths
                File file = new File(filePath);
                if (file.isDirectory()) {
                    // Process directory
                    Log.d(TAG, "Processing directory: " + filePath);
                    addFolderMetadata(file, metadata);
                } else if (file.isFile()) {
                    // Handle individual file
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", file.getAbsolutePath());
                    fileMetadata.put("size", file.length());
                    metadata.put(fileMetadata);
                    Log.d(TAG, "Added file metadata: " + fileMetadata.toString());
                } else {
                    Log.e(TAG, "File not found or not valid: " + filePath);
                }
            }
        }

        // Log metadata before saving
        Log.d(TAG, "Metadata before saving: " + metadata.toString());

        // Save metadata to a JSON file in the specified directory
        Log.d(TAG, "Saving metadata to file: " + metadataFilePath);
        try {
            saveMetadataToFile(metadataFilePath, metadata);
            metadataCreated = true;
        } catch (IOException e) {
            Log.e(TAG, "Failed to create metadata: " + e.getMessage(), e);
            metadataCreated = false;
        }

        return metadataFilePath;
    }

    private void addFolderMetadataFromDocumentFile(DocumentFile folder, JSONArray metadata) throws JSONException {
        Log.d(TAG, "Traversing DocumentFile folder: " + folder.getUri().toString());
        DocumentFile[] files = folder.listFiles();
        if (files != null) {
            for (DocumentFile file : files) {
                JSONObject fileMetadata = new JSONObject();
                fileMetadata.put("path", file.getName());
                fileMetadata.put("size", file.isDirectory() ? 0 : file.length());
                metadata.put(fileMetadata);
                Log.d(TAG, "Added metadata: " + fileMetadata.toString());

                // If it's a directory, recurse into it
                if (file.isDirectory()) {
                    addFolderMetadataFromDocumentFile(file, metadata);
                }
            }
        } else {
            Log.e(TAG, "Could not list files for directory: " + folder.getUri().toString());
        }
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

    private void addFolderMetadata(File folder, JSONArray metadata) throws IOException, JSONException {
        Log.d(TAG, "Traversing folder: " + folder.getAbsolutePath());
        File[] files = folder.listFiles();
        if (files != null) {
            for (File file : files) {
                JSONObject fileMetadata = new JSONObject();
                String relativePath = folder.getAbsolutePath();
                fileMetadata.put("path", relativePath + "/" + file.getName());
                fileMetadata.put("size", file.isDirectory() ? 0 : file.length());
                metadata.put(fileMetadata);
                Log.d(TAG, "Added metadata: " + fileMetadata.toString());

                // If it's a directory, recurse into it
                if (file.isDirectory()) {
                    addFolderMetadata(file, metadata);
                }
            }
        } else {
            Log.e(TAG, "Could not list files for directory: " + folder.getAbsolutePath());
        }
    }

    private String readMetadataFile(String filePath) throws IOException {
        StringBuilder metadataContent = new StringBuilder();
        try {
            File metadataFile = new File(filePath);
            if (metadataFile.exists()) {
                try (FileReader fileReader = new FileReader(metadataFile);
                     BufferedReader bufferedReader = new BufferedReader(fileReader)) {
                    String line;
                    while ((line = bufferedReader.readLine()) != null) {
                        metadataContent.append(line);
                    }
                }
            } else {
                Log.e(TAG, "Metadata file not found: " + filePath);
            }
        } catch (IOException e) {
            Log.e(TAG, "Error reading metadata file: " + e.getMessage(), e);
            throw e;
        }
        return metadataContent.toString();
    }

    private void refreshRecyclerView() {
        // Re-create the adapter and attach it to the RecyclerView
        fileAdapter = new FileAdapter(filePaths);
        recyclerView.setAdapter(fileAdapter);
        fileAdapter.notifyDataSetChanged();
    }
}
