package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.util.Log;
import android.widget.Button;
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import java.util.ArrayList;
import java.util.List;

public class SendFileActivityPython extends AppCompatActivity {

    private String receiverJson;
    private List<String> filePaths = new ArrayList<>();
    private FileAdapter fileAdapter;
    private RecyclerView recyclerView;

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

        // Log and send the selected file/folder paths
        if (!filePaths.isEmpty()) {
            Log.d("SendFileActivity", "Files to send: " + filePaths);
            Toast.makeText(this, "Files selected: " + filePaths.size(), Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "No files or folder selected", Toast.LENGTH_SHORT).show();
        }
    }

    private void refreshRecyclerView() {
        // Re-create the adapter and attach it to the RecyclerView
        fileAdapter = new FileAdapter(filePaths);
        recyclerView.setAdapter(fileAdapter);
        fileAdapter.notifyDataSetChanged();
    }
}