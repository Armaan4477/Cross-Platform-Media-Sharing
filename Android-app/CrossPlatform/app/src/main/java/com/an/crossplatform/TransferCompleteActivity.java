package com.an.crossplatform;

import android.os.Bundle;
import android.widget.Button;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class TransferCompleteActivity extends AppCompatActivity {

    private Button doneButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_transfer_complete);

        doneButton = findViewById(R.id.done_button);
        doneButton.setOnClickListener(v -> {
            Toast.makeText(this, "App Exit Completed", Toast.LENGTH_SHORT).show();
            finishAffinity(); // Close all activities and return to main screen
        });
    }

    @Override
    public void onBackPressed() {
        super.onBackPressed();
        finishAffinity(); // Ensure consistent navigation
    }
}