package com.an.crossplatform;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        createConfigFileIfNotExists();

        Button btnSend = findViewById(R.id.btn_send);
        Button btnReceive = findViewById(R.id.btn_receive);
        ImageButton btnPreferences = findViewById(R.id.btn_preferences);

        btnSend.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, DiscoverDevicesActivity.class);
            startActivity(intent);
        });

        btnReceive.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, WaitingToReceiveActivity.class);
            startActivity(intent);
        });

        btnPreferences.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, PreferencesActivity.class);
            startActivity(intent);
        });
    }

    private void createConfigFileIfNotExists() {
        try {
            // Use internal storage for folder
            File folder = new File(getFilesDir(), "config");
            if (!folder.exists()) {
                boolean folderCreated = folder.mkdir();
                if (!folderCreated) {
                    Log.e("MainActivity", "Failed to create config folder");
                    return;
                }
            }

            // Create config.json inside the folder
            File file = new File(folder, "config.json");
            if (!file.exists()) {
                boolean fileCreated = file.createNewFile();
                if (fileCreated) {
                    // Create default JSON content and write to the file
                    JSONObject jsonObject = new JSONObject();
                    // Change device_name to be the model of the device
                    String deviceName = Build.MODEL;
                    jsonObject.put("device_name", deviceName);
                    jsonObject.put("saveToPath", "Download Folder");
                    jsonObject.put("maxFileSize", 1000000);  // 1 MB
                    jsonObject.put("encryption", false);

                    // Write JSON data to the file
                    try (FileOutputStream fileOutputStream = new FileOutputStream(file)) {
                        fileOutputStream.write(jsonObject.toString().getBytes());
                        Log.d("MainActivity", "Config file created and written successfully.");
                    }
                } else {
                    Log.e("MainActivity", "Failed to create config.json");
                }
            } else {
                Log.d("MainActivity", "Config file already exists.");
            }
        } catch (Exception e) {
            Log.e("MainActivity", "Error creating or writing to config.json", e);
        }
    }
}