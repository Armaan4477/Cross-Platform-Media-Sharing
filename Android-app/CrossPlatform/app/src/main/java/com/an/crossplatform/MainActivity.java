package com.an.crossplatform;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.PackageInfo;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

import android.content.Context;
import android.app.AlertDialog;
import android.net.ConnectivityManager;
import android.widget.Toast;


public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_CODE_STORAGE_PERMISSION = 1;
    private static final int REQUEST_CODE_MANAGE_STORAGE_PERMISSION = 2;
    private static boolean isFirstLaunch = true;
    private static final String CONFIG_FILE_NAME = "config.json";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        FileLogger.init(this);
        getVersionName();
        requestStoragePermissions();

        createConfigFileIfNotExists();
        //createsavefolder();
        checkForUpdates();
        forceReleasePort();


        Button btnSend = findViewById(R.id.btn_send);
        Button btnReceive = findViewById(R.id.btn_receive);
        ImageButton btnPreferences = findViewById(R.id.btn_preferences);

        btnSend.setOnClickListener(v -> {
            if (!isWifiConnected()) {
                showNetworkWarning("Please note: No Wifi connection detected. Connection to other devices may fail.",
                        true,
                        () -> startActivity(new Intent(MainActivity.this, DiscoverDevicesActivity.class)));
                return;
            }

            if (shouldShowWarning()) {
                showNetworkWarning(
                        "Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.",
                        false,
                        () -> startActivity(new Intent(MainActivity.this, DiscoverDevicesActivity.class))
                );
            } else {
                startActivity(new Intent(MainActivity.this, DiscoverDevicesActivity.class));
            }
        });

        btnReceive.setOnClickListener(v -> {
            if (!isWifiConnected()) {
                showNetworkWarning("Please note: No Wifi connection detected. Connection to other devices may fail.",
                        true,
                        () -> startActivity(new Intent(MainActivity.this, WaitingToReceiveActivity.class)));
                return;
            }

            if (shouldShowWarning()) {
                showNetworkWarning(
                        "Before starting the transfer, please ensure both the sender and receiver devices are connected to the same network.",
                        false,
                        () -> startActivity(new Intent(MainActivity.this, WaitingToReceiveActivity.class))
                );
            } else {
                startActivity(new Intent(MainActivity.this, WaitingToReceiveActivity.class));
            }
        });

        btnPreferences.setOnClickListener(v -> {
            startActivity(new Intent(MainActivity.this, PreferencesActivity.class));
        });
        // Handle back button press using OnBackPressedDispatcher
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                // Ask user to confirm exit
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Exit")
                        .setMessage("Are you sure you want to exit?")
                        .setPositiveButton("Yes", (dialog, which) -> {
                            dialog.dismiss();
                            finishAffinity(); // Close all activities
                            android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
                            System.exit(0); // Ensure complete shutdown
                        })
                        .setNegativeButton("No", (dialog, which) -> dialog.dismiss())
                        .show();
            }
        });
    }

    private String getVersionName() {
        try {
            // Fetch version name from the app's PackageInfo
            PackageInfo packageInfo = getPackageManager().getPackageInfo(getPackageName(), 0);
            String versionName = packageInfo.versionName;

            // Log the version name
            FileLogger.log("AppVersion", "Version Name: " + versionName);

            return versionName;
        } catch (PackageManager.NameNotFoundException e) {
            e.printStackTrace();
            FileLogger.log("AppVersion", "Version Name not found", e);
            return "Unknown";
        }

    }

    private void requestStoragePermissions() {
        if (!Environment.isExternalStorageManager()) {
            AlertDialog.Builder builder = new AlertDialog.Builder(this);
            builder.setTitle("Permission Required")
                    .setMessage("This app needs access to manage all files on your device to save the transferred files. Please grant the permission by clicking the grant button then allowing access to the app.")
                    .setPositiveButton("Grant Permission", (dialog, which) -> {
                        Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                                Uri.parse("package:" + getPackageName()));
                        startActivityForResult(intent, REQUEST_CODE_MANAGE_STORAGE_PERMISSION);
                    })
                    .setNegativeButton("Cancel", (dialog, which) -> {
                        dialog.dismiss();
                        Toast.makeText(this, "Storage permission is required. App will close.",
                                Toast.LENGTH_SHORT).show();
                        finish();
                    })
                    .setCancelable(false)
                    .show();
        }
    }

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

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_CODE_MANAGE_STORAGE_PERMISSION) {
            if (Environment.isExternalStorageManager()) {
                Toast.makeText(this, "All files access granted", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "All files access permission denied. App will close.",
                        Toast.LENGTH_SHORT).show();
                finish();
            }
        }
    }

    private void createConfigFileIfNotExists() {
        try {
            File configDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config");
            FileLogger.log("MainActivity", "Config directory path: " + configDir.getAbsolutePath());

            if (!configDir.exists()) {
                boolean folderCreated = configDir.mkdirs();
                if (!folderCreated) {
                    FileLogger.log("MainActivity", "Failed to create config directory");
                    return;
                }
            }

            File file = new File(configDir, "config.json");
            String currentVersion = getVersionName();
            String existingDeviceName = Build.MODEL;
            String existingSaveToDirectory = null;
            boolean existingEncryption = false;
            boolean shouldCreateFile = !file.exists();

            // Read existing config if it exists
            if (file.exists()) {
                try {
                    String content = new String(java.nio.file.Files.readAllBytes(file.toPath()));
                    JSONObject existingConfig = new JSONObject(content);
                    String configVersion = existingConfig.optString("json_version", "");

                    if (configVersion.equals(currentVersion)) {
                        FileLogger.log("MainActivity", "Config file is up to date.");
                        return;
                    }

                    // Preserve existing values
                    existingDeviceName = existingConfig.optString("device_name", Build.MODEL);
                    existingSaveToDirectory = existingConfig.optString("saveToDirectory", null);
                    existingEncryption = existingConfig.optBoolean("encryption", false);
                    shouldCreateFile = true;

                    FileLogger.log("MainActivity", "Config version mismatch. Updating config file.");
                } catch (Exception e) {
                    FileLogger.log("MainActivity", "Error reading existing config", e);
                    shouldCreateFile = true;
                }
            }

            if (shouldCreateFile) {
                if (file.exists()) {
                    file.delete();
                }
                boolean fileCreated = file.createNewFile();
                if (fileCreated) {
                    JSONObject jsonObject = new JSONObject();

                    // Set up default save directory if not preserved from existing config
                    if (existingSaveToDirectory == null) {
                        File mediaDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");
                        if (!mediaDir.exists()) {
                            boolean dirCreated = mediaDir.mkdirs();
                            if (!dirCreated) {
                                FileLogger.log("MainActivity", "Failed to create media directory");
                                return;
                            }
                        }
                        existingSaveToDirectory = mediaDir.getAbsolutePath();
                        if (existingSaveToDirectory.startsWith("/storage/emulated/0")) {
                            existingSaveToDirectory = existingSaveToDirectory.replace("/storage/emulated/0", "");
                        }
                    }

                    // Create JSON with preserved/default values
                    jsonObject.put("json_version", currentVersion);
                    jsonObject.put("device_name", existingDeviceName);
                    jsonObject.put("saveToDirectory", existingSaveToDirectory);
                    jsonObject.put("maxFileSize", 1000000);
                    jsonObject.put("encryption", existingEncryption);
                    jsonObject.put("show_warn", true);
                    jsonObject.put("auto_check", true);
                    jsonObject.put("update_channel", "stable");

                    try (FileOutputStream fileOutputStream = new FileOutputStream(file)) {
                        fileOutputStream.write(jsonObject.toString().getBytes());
                        FileLogger.log("MainActivity", "Config file created/updated successfully.");
                    }
                } else {
                    FileLogger.log("MainActivity", "Failed to create config.json");
                }
            }
        } catch (Exception e) {
            FileLogger.log("MainActivity", "Error creating or writing to config.json", e);
        }
    }

    private boolean shouldShowWarning() {
        try {
            File configFile = new File(Environment.getExternalStorageDirectory(),
                    "Android/media/" + getPackageName() + "/Config/config.json");
            if (configFile.exists()) {
                String content = new String(java.nio.file.Files.readAllBytes(configFile.toPath()));
                JSONObject config = new JSONObject(content);
                return config.optBoolean("show_warn", true);
            }
        } catch (Exception e) {
            FileLogger.log("MainActivity", "Error reading show_warn from config", e);
        }
        return true;
    }

    private boolean isWifiConnected() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) return false;

        Network activeNetwork = cm.getActiveNetwork();
        if (activeNetwork == null) return false;

        NetworkCapabilities capabilities = cm.getNetworkCapabilities(activeNetwork);
        if (capabilities == null) return false;

        return capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
    }

    private void showNetworkStatusDialog(String message, boolean isError, Runnable onPositive) {
        if (!shouldShowWarning()) {
            if (onPositive != null) onPositive.run();
            return;
        }

        new AlertDialog.Builder(this)
                .setTitle("Warning")
                .setMessage(message)
                .setPositiveButton("OK", (dialog, which) -> {
                    dialog.dismiss();
                    if (!isError && onPositive != null) {
                        onPositive.run();
                    }
                })
                .show();
    }

    private void showNetworkWarning(String message, boolean isNoConnection, Runnable onContinue) {
        if (!shouldShowWarning()) {
            if (onContinue != null) onContinue.run();
            return;
        }

        new AlertDialog.Builder(this)
                .setTitle("Warning")
                .setMessage(message)
                .setPositiveButton("Continue", (dialog, which) -> {
                    dialog.dismiss();
                    if (onContinue != null) {
                        onContinue.run();
                    }
                })
                .show();
    }

    private boolean shouldAutoCheck() {
        try {
            File configFile = new File(Environment.getExternalStorageDirectory(),
                    "Android/media/" + getPackageName() + "/Config/config.json");
            if (configFile.exists()) {
                String content = new String(java.nio.file.Files.readAllBytes(configFile.toPath()));
                JSONObject config = new JSONObject(content);
                return config.optBoolean("auto_check", true);
            }
        } catch (Exception e) {
            FileLogger.log("MainActivity", "Error reading auto_check from config", e);
        }
        return true;
    }

    private void checkForUpdates() {
        String channel = loadchannel();
        if (!isFirstLaunch || !shouldAutoCheck()) {
            isFirstLaunch = false;
            return;
        }

        if (!isNetworkAvailable()) {
            FileLogger.log("CheckForUpdates", "No network connection available");
            isFirstLaunch = false;
            return;
        }

        new Thread(() -> {
            String apiVersion = null;
            HttpURLConnection connection = null;
            int retryCount = 0;
            int maxRetries = 2;

            while (retryCount <= maxRetries && apiVersion == null) {
                try {
                    URL url;
                    if (channel.equals("beta")) {
                        url = new URL("https://datadashshare.vercel.app/api/platformNumberbeta?platform=android");
                    } else {
                        url = new URL("https://datadashshare.vercel.app/api/platformNumber?platform=android");
                    }

                    connection = (HttpURLConnection) url.openConnection();
                    connection.setRequestMethod("GET");
                    connection.setConnectTimeout(5000);
                    connection.setReadTimeout(5000);

                    int responseCode = connection.getResponseCode();
                    if (responseCode == 200) {
                        try (BufferedReader reader = new BufferedReader(
                                new InputStreamReader(connection.getInputStream()))) {
                            StringBuilder response = new StringBuilder();
                            String line;
                            while ((line = reader.readLine()) != null) {
                                response.append(line);
                            }
                            JSONObject jsonObject = new JSONObject(response.toString());
                            apiVersion = jsonObject.getString("value");
                        }
                    }
                } catch (Exception e) {
                    FileLogger.log("CheckForUpdates",
                            "Attempt " + (retryCount + 1) + " failed: " + e.getMessage());
                    retryCount++;

                    if (retryCount <= maxRetries) {
                        try {
                            Thread.sleep(1000 * retryCount); // Exponential backoff
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                }
            }

            isFirstLaunch = false;
            String finalApiVersion = apiVersion;
            new Handler(Looper.getMainLooper()).post(() ->
                    processVersionCheckResult(finalApiVersion));
        }).start();
    }

    private String loadchannel() {
        String jsonString = readJsonFromFile();
        try {
            if (jsonString != null) {
                JSONObject configJson = new JSONObject(jsonString);
                return configJson.optString("update_channel", "stable");
            }
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error loading update channel", e);
        }
        return "stable";
    }

    private String readJsonFromFile() {
        File folder = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config");
        File file = new File(folder, CONFIG_FILE_NAME);

        if (file.exists()) {
            StringBuilder jsonString = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file)))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                FileLogger.log("PreferencesActivity", "Read JSON from file: " + jsonString.toString());
                return jsonString.toString();
            } catch (Exception e) {
                FileLogger.log("PreferencesActivity", "Error reading JSON from file", e);
            }
        } else {
            FileLogger.log("PreferencesActivity", "File does not exist: " + file.getAbsolutePath());
        }
        return null;
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) return false;

        Network activeNetwork = cm.getActiveNetwork();
        if (activeNetwork == null) return false;

        NetworkCapabilities capabilities = cm.getNetworkCapabilities(activeNetwork);
        return capabilities != null &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
    }

    private void processVersionCheckResult(String apiVersion) {
        if (apiVersion != null) {
            try {
                String appVersion = getVersionName();
                String[] apiParts = apiVersion.split("\\.");
                String[] appParts = appVersion.split("\\.");

                int[] apiNums = new int[Math.max(3, apiParts.length)];
                int[] appNums = new int[Math.max(3, appParts.length)];

                for (int i = 0; i < apiParts.length; i++) {
                    apiNums[i] = Integer.parseInt(apiParts[i]);
                }
                for (int i = 0; i < appParts.length; i++) {
                    appNums[i] = Integer.parseInt(appParts[i]);
                }

                for (int i = 0; i < Math.max(apiNums.length, appNums.length); i++) {
                    if (apiNums[i] < appNums[i]) {
                        return;
                    } else if (apiNums[i] > appNums[i]) {
                        showMessageDialog("Update Available",
                                "A newer version (" + apiVersion + ") is available. Please update your app.",
                                true);
                        return;
                    }
                }

                return;

            } catch (Exception e) {
                FileLogger.log("CheckForUpdates", "Error parsing version", e);
                showMessageDialog("Error", "Error checking for updates.", false);
            }
        } else {
            showMessageDialog("Error", "Failed to check for updates.", false);
        }
    }

    private void showMessageDialog(String title, String message, boolean showDownloadsButton) {
        androidx.appcompat.app.AlertDialog.Builder builder = new androidx.appcompat.app.AlertDialog.Builder(this);
        builder.setTitle(title)
                .setMessage(message)
                .setPositiveButton("Close", (dialog, which) -> {
                    dialog.dismiss();
                });

        if (showDownloadsButton) {
            builder.setNegativeButton("Open Settings Page", (dialog, which) -> {
                startActivity(new Intent(MainActivity.this, PreferencesActivity.class));
            });
        }

        androidx.appcompat.app.AlertDialog dialog = builder.create();
        dialog.show();
    }

    private class PortReleaseUDPThread extends Thread {
        @Override
        public void run() {
            int port1 = 49185;
            int port2 = 49186;
            try {
                // Find and kill process using the UDP port
                Process process = Runtime.getRuntime().exec("lsof -i udp:" + port1);
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line;

                while ((line = reader.readLine()) != null) {
                    if (!line.startsWith("COMMAND")) {
                        String[] parts = line.trim().split("\\s+");
                        if (parts.length > 1) {
                            String pid = parts[1];
                            Runtime.getRuntime().exec("kill -9 " + pid);
                            FileLogger.log("DiscoverDevices", "Killed process " + pid + " using UDP port " + port1);
                        }
                    }
                }

            } catch (Exception e) {
                FileLogger.log("DiscoverDevices", "Error releasing UDP port: " + port1, e);
            }

            try {
                // Find and kill process using the UDP port
                Process process = Runtime.getRuntime().exec("lsof -i udp:" + port2);
                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line;

                while ((line = reader.readLine()) != null) {
                    if (!line.startsWith("COMMAND")) {
                        String[] parts = line.trim().split("\\s+");
                        if (parts.length > 1) {
                            String pid = parts[1];
                            Runtime.getRuntime().exec("kill -9 " + pid);
                            FileLogger.log("DiscoverDevices", "Killed process " + pid + " using UDP port " + port2);
                        }
                    }
                }

            } catch (Exception e) {
                FileLogger.log("DiscoverDevices", "Error releasing UDP port: " + port2, e);
            }
        }
    }
    private class PortReleaseThread extends Thread {
    @Override
    public void run() {
        int port1 =54314;
        int port2=57341;
        int port3=63152;
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port1);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port1);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port1, e);
        }
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port2);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port2);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port2, e);
        }
        try {
            // Find and kill process using the port
            Process process = Runtime.getRuntime().exec("lsof -i tcp:" + port3);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.contains("LISTEN")) {
                    String[] parts = line.split("\\s+");
                    if (parts.length > 1) {
                        String pid = parts[1];
                        Runtime.getRuntime().exec("kill -9 " + pid);
                        FileLogger.log("ReceiveFileActivity", "Killed process " + pid + " using port " + port3);
                    }
                }
            }
        } catch (Exception e) {
            FileLogger.log("ReceiveFileActivity", "Error releasing port: " + port3, e);
        }
     }
    }

    private void forceReleasePort() {
    new PortReleaseThread().start();
    new PortReleaseUDPThread().start();
}

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isFinishing()) {
            isFirstLaunch = true;
        }
    }

//    @Override
//    public void onBackPressed() {
//        super.onBackPressed();
//        // Ask user to confirm exit
//        new AlertDialog.Builder(this)
//                .setTitle("Exit")
//                .setMessage("Are you sure you want to exit?")
//                .setPositiveButton("Yes", (dialog, which) -> {
//                    dialog.dismiss();
//                    finishAffinity(); // Close all activities
//                    android.os.Process.killProcess(android.os.Process.myPid()); // Kill the app process
//                    System.exit(0); // Ensure complete shutdown
//                })
//                .setNegativeButton("No", (dialog, which) -> dialog.dismiss())
//                .show();
//    }


//    private void createsavefolder() {
//        try {
//            // Set up the path to the Downloads/DataDash directory
//            File downloadDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");
//            FileLogger.log("MainActivity", "DataDash download directory path: " + downloadDir.getAbsolutePath());
//
//            // Create the DataDash directory if it doesn't exist
//            if (!downloadDir.exists()) {
//                boolean folderCreated = downloadDir.mkdirs();
//                if (!folderCreated) {
//                    FileLogger.log("MainActivity", "Failed to create DataDash download directory");
//                    return;
//                } else {
//                    FileLogger.log("MainActivity", "DataDash download directory created successfully");
//                }
//            } else {
//                FileLogger.log("MainActivity", "DataDash download directory already exists");
//            }
//
//        } catch (Exception e) {
//            FileLogger.log("MainActivity", "Error creating DataDash download directory", e);
//        }
//    }

}