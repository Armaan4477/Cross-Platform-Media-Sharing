package com.an.crossplatform;

import android.os.Bundle;
import android.widget.Button;
import android.widget.Toast;
import androidx.activity.OnBackPressedCallback;

import androidx.appcompat.app.AppCompatActivity;

public class TransferCompleteActivity extends AppCompatActivity {

    private Button doneButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_transfer_complete);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                Toast.makeText(TransferCompleteActivity.this, "Back navigation is disabled, Please use the Done button", Toast.LENGTH_SHORT).show();
                // Do nothing to disable back navigation
            }
        });

        doneButton = findViewById(R.id.done_button);
        doneButton.setOnClickListener(v -> {
            Toast.makeText(this, "App Exit Completed", Toast.LENGTH_SHORT).show();
            finishAffinity(); // Close all activities
            android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
            System.exit(0); // Ensure complete shutdown
        });
    }

    @Override
    public void onBackPressed() {
        super.onBackPressed();
        finishAffinity(); // Ensure consistent navigation
    }
}