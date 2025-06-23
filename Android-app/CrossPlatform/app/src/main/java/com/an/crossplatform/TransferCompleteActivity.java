package com.an.crossplatform;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.Window;
import android.widget.Button;
import android.widget.Toast;

public class TransferCompleteActivity extends Dialog {

    private Button doneButton;
    private Button mainMenuButton;
    private Activity activity;

    public TransferCompleteActivity(Activity activity) {
        super(activity);
        this.activity = activity;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Remove the title bar
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.activity_transfer_complete);

        doneButton = findViewById(R.id.done_button);
        doneButton.setOnClickListener(v -> {
            Toast.makeText(activity, "App Exit Completed", Toast.LENGTH_SHORT).show();
            activity.finishAffinity(); // Close all activities
            android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
            System.exit(0); // Ensure complete shutdown
        });

        mainMenuButton = findViewById(R.id.main_menu_button);
        mainMenuButton.setOnClickListener(v -> {
            Toast.makeText(activity, "Main Menu", Toast.LENGTH_SHORT).show();
            dismiss();
            Intent intent = new Intent(activity, MainActivity.class);
            activity.startActivity(intent);
        });
    }
}