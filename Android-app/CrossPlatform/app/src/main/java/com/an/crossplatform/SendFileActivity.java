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
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class SendFileActivity extends AppCompatActivity {

    private String receiverJson;
    private List<String> filePaths = new ArrayList<>();
    private FileAdapter fileAdapter;
    private RecyclerView recyclerView;
    private boolean metadataCreated = false;
    private String metadataFilePath = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_send);

        // Retrieve the JSON string from the intent
        receiverJson = getIntent().getStringExtra("receiverJson");
        Log.d("SendFileActivity", "Received JSON: " + receiverJson);

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
        Log.d("SendFileActivity", "Metadata created: " + metadataCreated);
    }

    private String createMetadata() throws IOException, JSONException {
        JSONArray metadata = new JSONArray();

        // Check if we are working with a folder or a list of files
        if (filePaths.size() == 1 && isFolder(filePaths.get(0))) {
            // Handle folder case
            String folderPath = filePaths.get(0);
            File folder = new File(Uri.parse(folderPath).getPath());

            if (folder.isDirectory()) {
                // Recursively list files and directories
                addFolderMetadata(folder, folder, metadata);
            }

            // Save metadata to a JSON file in the selected folder
            String metadataFilePath = folder.getAbsolutePath() + "/metadata.json";
            saveMetadataToFile(metadataFilePath, metadata);
            metadataCreated = true;
            return metadataFilePath;
        } else {
            // Handle individual files case
            for (String filePath : filePaths) {
                File file = new File(Uri.parse(filePath).getPath());
                if (file.isFile()) {
                    JSONObject fileMetadata = new JSONObject();
                    fileMetadata.put("path", file.getName());
                    fileMetadata.put("size", file.length());
                    metadata.put(fileMetadata);
                }
            }

            // Save metadata to a JSON file in the same directory as the first file
            File firstFile = new File(Uri.parse(filePaths.get(0)).getPath());
            String metadataFilePath = firstFile.getParent() + "/metadata.json";
            saveMetadataToFile(metadataFilePath, metadata);
            metadataCreated = true;
            return metadataFilePath;
        }
    }

    private void addFolderMetadata(File baseFolder, File currentFolder, JSONArray metadata) throws IOException, JSONException {
        File[] files = currentFolder.listFiles();
        if (files != null) {
            for (File file : files) {
                JSONObject fileMetadata = new JSONObject();
                String relativePath = baseFolder.toURI().relativize(file.toURI()).getPath();
                fileMetadata.put("path", relativePath);
                fileMetadata.put("size", file.isDirectory() ? 0 : file.length());
                metadata.put(fileMetadata);

                if (file.isDirectory()) {
                    // Recurse into subdirectories
                    addFolderMetadata(baseFolder, file, metadata);
                }
            }
        }
    }

    private void saveMetadataToFile(String metadataFilePath, JSONArray metadata) throws IOException {
        try (FileWriter fileWriter = new FileWriter(metadataFilePath)) {
            fileWriter.write(metadata.toString());
            fileWriter.flush();
        }
    }

    private boolean isFolder(String path) {
        File file = new File(Uri.parse(path).getPath());
        return file.isDirectory();
    }

    private void refreshRecyclerView() {
        // Re-create the adapter and attach it to the RecyclerView
        fileAdapter = new FileAdapter(filePaths);
        recyclerView.setAdapter(fileAdapter);
        fileAdapter.notifyDataSetChanged();
    }
}
