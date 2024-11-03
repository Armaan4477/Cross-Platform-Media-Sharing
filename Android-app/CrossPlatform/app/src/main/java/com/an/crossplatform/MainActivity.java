package com.an.crossplatform;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.util.Log;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import android.content.Context;
import android.app.AlertDialog;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.widget.Toast;


public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_CODE_STORAGE_PERMISSION = 1;
    private static final int REQUEST_CODE_MANAGE_STORAGE_PERMISSION = 2;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        requestStoragePermissions();

        createConfigFileIfNotExists();
        //createdownloadfolder();

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

    private void requestStoragePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            // For Android 11 and above
            if (!Environment.isExternalStorageManager()) {
                // Request MANAGE_EXTERNAL_STORAGE permission
                Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                        Uri.parse("package:" + getPackageName()));
                startActivityForResult(intent, REQUEST_CODE_MANAGE_STORAGE_PERMISSION);
            }
        } else {
            // For Android 10 and below
            ActivityCompat.requestPermissions(this, new String[]{
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE
            }, REQUEST_CODE_STORAGE_PERMISSION);
        }
    }

    // Handle the result from permissions dialog
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == REQUEST_CODE_STORAGE_PERMISSION) {
            // Check if permissions are granted
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Storage permission granted", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Storage permission denied", Toast.LENGTH_SHORT).show();
            }
        }
    }

    // Handle result for Android 11 MANAGE_EXTERNAL_STORAGE request
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_CODE_MANAGE_STORAGE_PERMISSION) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                if (Environment.isExternalStorageManager()) {
                    Toast.makeText(this, "All files access granted", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(this, "All files access permission denied", Toast.LENGTH_SHORT).show();
                }
            }
        }
    }

    private void createConfigFileIfNotExists() {
        try {
            // Use external storage for the folder path
            File configDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config");
            Log.e("MainActivity", "Config directory path: " + configDir.getAbsolutePath());
            // Create the config directory if it doesn't exist
            if (!configDir.exists()) {
                boolean folderCreated = configDir.mkdirs();
                if (!folderCreated) {
                    Log.e("MainActivity", "Failed to create config directory");
                    return;
                }
            }

            // Create config.json inside the folder
            File file = new File(configDir, "config.json");
            if (!file.exists()) {
                boolean fileCreated = file.createNewFile();
                if (fileCreated) {
                    // Create default JSON content and write to the file
                    JSONObject jsonObject = new JSONObject();
                    String deviceName = Build.MODEL;  // Device name

                    // Set the saveToDirectory to the Android/media folder within external storage
                    // Correctly construct the media directory path
                    File mediaDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");

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

//    private void createdownloadfolder() {
//        try {
//            // Set up the path to the Downloads/DataDash directory
//            File downloadDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");
//            Log.e("MainActivity", "DataDash download directory path: " + downloadDir.getAbsolutePath());
//
//            // Create the DataDash directory if it doesn't exist
//            if (!downloadDir.exists()) {
//                boolean folderCreated = downloadDir.mkdirs();
//                if (!folderCreated) {
//                    Log.e("MainActivity", "Failed to create DataDash download directory");
//                    return;
//                } else {
//                    Log.d("MainActivity", "DataDash download directory created successfully");
//                }
//            } else {
//                Log.d("MainActivity", "DataDash download directory already exists");
//            }
//
//        } catch (Exception e) {
//            Log.e("MainActivity", "Error creating DataDash download directory", e);
//        }
//    }

}