package com.an.crossplatform;

import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import androidx.appcompat.app.AppCompatActivity;

public class SendFileActivity extends AppCompatActivity {

    private String receiverJson;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_send);

        // Retrieve the JSON string from the intent
        receiverJson = getIntent().getStringExtra("receiverJson");
        Log.d("SendFileActivity", "Received JSON: " + receiverJson);

        // Set up buttons
        Button selectFileButton = findViewById(R.id.btn_select_file);
        Button sendButton = findViewById(R.id.btn_send);

        // Set up button click listeners
        selectFileButton.setOnClickListener(v -> {
            onSelectFileClicked();
        });

        sendButton.setOnClickListener(v -> {
            onSendClicked();
        });
    }

    private void onSelectFileClicked() {
        Log.d("SendFileActivity", "Select File button clicked");
        // This is where you'd implement the file selection logic
    }

    private void onSendClicked() {
        Log.d("SendFileActivity", "Send button clicked");
        // This is where you'd implement the send logic
    }
}
