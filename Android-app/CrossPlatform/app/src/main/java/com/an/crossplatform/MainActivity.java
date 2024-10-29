package com.an.crossplatform;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import android.content.Context;
import android.app.AlertDialog;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;

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
            // Give a warning if the device is not connected to a network
//            if (!isNetworkConnected()) {
//                AlertDialog.Builder builder = new AlertDialog.Builder(this);
//                builder.setTitle("Warning")
//                        .setMessage("Please connect to a network before sending files.")
//                        .setPositiveButton("OK", (dialog, which) -> dialog.dismiss())
//                        .show();
//                return;
//            }
            Intent intent = new Intent(MainActivity.this, DiscoverDevicesActivity.class);
            startActivity(intent);
        });

        btnReceive.setOnClickListener(v -> {
            // Give a warning if the device is not connected to a network
//            if (!isNetworkConnected()) {
//                AlertDialog.Builder builder = new AlertDialog.Builder(this);
//                builder.setTitle("Warning")
//                        .setMessage("Please connect to a network before receiving files.")
//                        .setPositiveButton("OK", (dialog, which) -> dialog.dismiss())
//                        .show();
//                return;
//            }
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
            // Use internal storage for folder (this is for the config file, unchanged)
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
                    String deviceName = Build.MODEL;  // Device name

                    // Set the saveToDirectory to the Android/media folder within external storage
                    // Correctly construct the media directory path
                    File mediaDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Media/");

                    // Create the media directory if it doesn't exist
                    if (!mediaDir.exists()) {
                        boolean dirCreated = mediaDir.mkdirs();  // Create the directory if it doesn't exist
                        if (!dirCreated) {
                            Log.e("MainActivity", "Failed to create media directory");
                            return;
                        }
                    }

                    // Get the full path to the media folder
                    String saveToDirectory = mediaDir.getAbsolutePath();

                    // Remove the "/storage/emulated/0" prefix if it exists
                    if (saveToDirectory.startsWith("/storage/emulated/0")) {
                        saveToDirectory = saveToDirectory.replace("/storage/emulated/0", ""); // Remove the prefix
                    }

                    jsonObject.put("device_name", deviceName);
                    jsonObject.put("saveToDirectory", saveToDirectory); // Updated saveToDirectory
                    Log.d("MainActivity", "saveToDirectory: " + saveToDirectory);
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