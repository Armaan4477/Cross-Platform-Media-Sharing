package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;
import android.widget.ImageButton;

import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.widget.TextView;

import android.os.Handler;
import android.os.Looper;
import java.net.HttpURLConnection;
import java.net.URL;
import androidx.appcompat.app.AlertDialog;


public class PreferencesActivity extends AppCompatActivity {

    private EditText deviceNameInput;
    private EditText saveToDirectoryInput;
    private Map<String, Object> originalPreferences = new HashMap<>();

    private static final String CONFIG_FOLDER_NAME = "config";
    private static final String CONFIG_FILE_NAME = "config.json";  // Config file stored in internal storage
    private ImageButton imageButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_preferences);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                goToMainMenu();
            }
        });

        deviceNameInput = findViewById(R.id.device_name_input);
        saveToDirectoryInput = findViewById(R.id.save_to_path_input);
        imageButton = findViewById(R.id.imageButton);

        Button resetDeviceNameButton = findViewById(R.id.device_name_reset_button);
        Button saveToDirectoryPickerButton = findViewById(R.id.save_to_path_picker_button);
        Button resetSavePathButton = findViewById(R.id.save_to_path_reset_button);
        Button submitButton = findViewById(R.id.submit_button);
        Button mainMenuButton = findViewById(R.id.main_menu_button);
        Button btnCredits = findViewById(R.id.btn_credits);

        // Set the app version
        TextView appVersionLabel = findViewById(R.id.app_version_label);
        appVersionLabel.setText("App Version: " + getVersionName());

        // Load saved preferences from internal storage
        loadPreferences();

        resetDeviceNameButton.setOnClickListener(v -> resetDeviceName());
        saveToDirectoryPickerButton.setOnClickListener(v -> pickDirectory());
        resetSavePathButton.setOnClickListener(v -> resetSavePath());
        submitButton.setOnClickListener(v -> submitPreferences());
        mainMenuButton.setOnClickListener(v -> goToMainMenu());
        imageButton.setOnClickListener(v -> openHelpMenu());
        btnCredits.setOnClickListener(v -> {
            Intent intent = new Intent(PreferencesActivity.this, CreditsActivity.class);
            startActivity(intent);
        });

        // Fetch version name and set it to the TextView
        String versionName = getVersionName();

        // Handle "Check for Update" button click
        Button checkForUpdateButton = findViewById(R.id.check_for_update_button);
        checkForUpdateButton.setOnClickListener(v -> checkForUpdates());
    }

    // Method to get version name dynamically
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

    private void checkForUpdates() {
        // Create a new thread for the network operation
        new Thread(() -> {
            String apiVersion = null;
            try {
                // Define the API URL
                URL url = new URL("https://datadashshare.vercel.app/api/platformNumber?platform=android");

                // Open a connection
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");

                // Check the response code
                int responseCode = connection.getResponseCode();
                if (responseCode == 200) { // Success
                    BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                    StringBuilder response = new StringBuilder();
                    String line;

                    // Read the response
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    reader.close();

                    // Parse the JSON response to extract the version value
                    JSONObject jsonObject = new JSONObject(response.toString());
                    apiVersion = jsonObject.getString("value");
                } else {
                    FileLogger.log("CheckForUpdates", "Failed to fetch version, Response Code: " + responseCode);
                }
            } catch (Exception e) {
                FileLogger.log("CheckForUpdates", "Error fetching updates", e);
            }

            // Process the result on the main thread
            String finalApiVersion = apiVersion;
            new Handler(Looper.getMainLooper()).post(() -> processVersionCheckResult(finalApiVersion));
        }).start();
    }

    // Method to process the version check result on the main thread
    private void processVersionCheckResult(String apiVersion) {
        if (apiVersion != null) {
            try {
                // Get the app's version
                String appVersion = getVersionName();

                // Split both versions into parts
                String[] apiParts = apiVersion.split("\\.");
                String[] appParts = appVersion.split("\\.");

                // Compare the versions part by part
                for (int i = 0; i < Math.min(apiParts.length, appParts.length); i++) {
                    int apiPart = Integer.parseInt(apiParts[i]);
                    int appPart = Integer.parseInt(appParts[i]);

                    if (apiPart > appPart) {
                        showMessageDialog("App is older", "Your app version is outdated. Please update to the latest version.", true);
                        return;
                    } else if (apiPart < appPart) {
                        showMessageDialog("Please downgrade", "Your app version is newer than the publicly available version. Downgrade to ensure compatibility.", true);
                        return;
                    }
                }

                // If all parts are equal
                showMessageDialog("Version is up to date", "Your app is up to date.", false);
            } catch (Exception e) {
                FileLogger.log("CheckForUpdates", "Error parsing version", e);
                showMessageDialog("Error", "Error checking for updates.", false);
            }
        } else {
            showMessageDialog("Error", "Failed to check for updates.", false);
        }
    }

    // Helper method to show a message
    private void showMessage(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    private void showMessageDialog(String title, String message, boolean showDownloadsButton) {
        // Build the dialog
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle(title)
                .setMessage(message)
                .setPositiveButton("Close", (dialog, which) -> {
                    dialog.dismiss(); // Dismiss the dialog when "Close" is clicked
                });

        if (showDownloadsButton) {
            builder.setNegativeButton("Open Beta Downloads Page", (dialog, which) -> {
                // Open the downloads page in a browser
                Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://datadashshare.vercel.app/download"));
                startActivity(browserIntent);
            });
        }

        // Show the dialog
        AlertDialog dialog = builder.create();
        dialog.show();
    }


    private void loadPreferences() {
        String jsonString = readJsonFromFile();

        if (jsonString != null) {
            try {
                JSONObject configJson = new JSONObject(jsonString);
                String deviceName = configJson.getString("device_name");
                String saveToDirectory = configJson.getString("saveToDirectory");

                // Store original preferences in a map
                originalPreferences.put("device_name", deviceName);
                originalPreferences.put("saveToDirectory", saveToDirectory);

                // Set the input fields with the retrieved values
                deviceNameInput.setText(deviceName);
                saveToDirectoryInput.setText(saveToDirectory);
            } catch (Exception e) {
                FileLogger.log("PreferencesActivity", "Error loading preferences", e);
                setDefaults();  // Fallback to default values if any error occurs
            }
        } else {
            setDefaults();  // Use default values if the file doesn't exist
        }
    }

    private void setDefaults() {
        // Set the saveToDirectory to the Android/media folder within external storage
        File mediaDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Media/");

        // Create the media directory if it doesn't exist
        if (!mediaDir.exists()) {
            boolean dirCreated = mediaDir.mkdirs();  // Create the directory if it doesn't exist
            if (!dirCreated) {
                FileLogger.log("PreferencesActivity", "Failed to create media directory");
                return;
            }
        }

        // Get the full path to the media folder
        String saveToDirectory = mediaDir.getAbsolutePath();

        // Set defaults for device name and saveToDirectory
        originalPreferences.put("device_name", "Android Device");
        originalPreferences.put("saveToDirectory", saveToDirectory);

        // Update UI fields with defaults
        deviceNameInput.setText("Android Device");
        saveToDirectoryInput.setText(saveToDirectory);
    }

    // Method to read JSON from internal storage
    private String readJsonFromFile() {
        // Get the external file path for the config directory
        File folder = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config"); // External storage path
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

    private void resetDeviceName() {
        deviceNameInput.setText(android.os.Build.MODEL);  // Reset device name to the device's model name
    }

    private void resetSavePath() {
        File mediaDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");

        // Create the media directory if it doesn't exist
        if (!mediaDir.exists()) {
            boolean dirCreated = mediaDir.mkdirs();  // Create the directory if it doesn't exist
            if (!dirCreated) {
                FileLogger.log("MainActivity", "Failed to create media directory");
                return;
            }
        }
        // Get the full path to the media folder
        String saveToDirectory = mediaDir.getAbsolutePath();

        // Remove the "/storage/emulated/0" prefix if it exists
        if (saveToDirectory.startsWith("/storage/emulated/0")) {
            saveToDirectory = saveToDirectory.replace("/storage/emulated/0", ""); // Remove the prefix
        }
        saveToDirectoryInput.setText(saveToDirectory);  // Reset save path to default
    }

    private void pickDirectory() {
        // Launch a directory picker
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        directoryPickerLauncher.launch(intent);
    }

    private final ActivityResultLauncher<Intent> directoryPickerLauncher =
            registerForActivityResult(new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                            Uri uri = result.getData().getData();
                            String pickedDir = uri.getPath();

                            // Check if the picked directory path is valid
                            if (pickedDir != null) {
                                // Ensure it starts with a slash
                                if (!pickedDir.startsWith("/")) {
                                    pickedDir = "/" + pickedDir;
                                }
                                // Ensure it ends with a slash
                                if (!pickedDir.endsWith("/")) {
                                    pickedDir += "/";
                                }
                            }

                            // Give a warning if the selected directory is within the "Download" folder and may cause issues
                            if (pickedDir.contains("Download")) {
                                Toast.makeText(this, "Warning: Selected directory is within the Download folder", Toast.LENGTH_SHORT).show();
                            }
                            saveToDirectoryInput.setText(pickedDir);
                        }
                    });

    private void submitPreferences() {
        String deviceName = deviceNameInput.getText().toString();
        String saveToDirectoryURI = saveToDirectoryInput.getText().toString();

        // Ensure the directory path ends with a slash
        if (!saveToDirectoryURI.startsWith("/")) {
            saveToDirectoryURI += "/";
        }

        // Ensure the directory path ends with a slash
        if (!saveToDirectoryURI.endsWith("/")) {
            saveToDirectoryURI += "/";
        }

        // Convert into a path like /storage/emulated/0/Download
        String saveToDirectory = saveToDirectoryURI.substring(saveToDirectoryURI.indexOf(":", 0) + 1);
        FileLogger.log("PreferencesActivity", "Save to path: " + saveToDirectory);

        if (deviceName.isEmpty()) {
            Toast.makeText(this, "Device Name cannot be empty", Toast.LENGTH_SHORT).show();
            return;
        }

        // Create a new JSON object with the updated preferences
        JSONObject configJson = new JSONObject();
        try {
            configJson.put("device_name", deviceName);
            configJson.put("saveToDirectory", saveToDirectory);
            configJson.put("max_file_size", 1000000);  // 1 MB
            configJson.put("encryption", false);

            // Save preferences to internal storage
            saveJsonToFile(configJson.toString());

            // Notify the user that preferences were updated
            Toast.makeText(this, "Settings updated", Toast.LENGTH_SHORT).show();
            FileLogger.log("PreferencesActivity", "Preferences updated: " + configJson.toString());
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error creating JSON", e);
        }

        // Go back to the main screen after submitting preferences
        goToMainMenu();
    }

    // Method to save the modified JSON to internal storage
    private void saveJsonToFile(String jsonString) {
        try {
            File folder = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config");  // External storage path
            if (!folder.exists()) {
                boolean folderCreated = folder.mkdirs();
                FileLogger.log("PreferencesActivity", "Config folder created: " + folder.getAbsolutePath());
                if (!folderCreated) {
                    FileLogger.log("PreferencesActivity", "Failed to create config folder");
                    return;
                }
            }

            File file = new File(folder, CONFIG_FILE_NAME);
            FileOutputStream fileOutputStream = new FileOutputStream(file);
            fileOutputStream.write(jsonString.getBytes());
            fileOutputStream.close();
            FileLogger.log("PreferencesActivity", "Preferences saved: " + jsonString);
            FileLogger.log("PreferencesActivity", "Preferences saved at: " + file.getAbsolutePath());
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error saving JSON to file", e);
        }
    }

    private void goToMainMenu() {
        Toast.makeText(this, "Settings Changes Discarded", Toast.LENGTH_SHORT).show();
        Intent mainIntent = new Intent(PreferencesActivity.this, MainActivity.class);
        startActivity(mainIntent);
        finish();
    }

    private void openHelpMenu() {
        // Open the help dialog
        HelpDialog helpDialog = new HelpDialog(this);
        helpDialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        helpDialog.show();
    }
}