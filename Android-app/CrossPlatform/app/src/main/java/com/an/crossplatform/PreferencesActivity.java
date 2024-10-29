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

        deviceNameInput = findViewById(R.id.device_name_input);
        saveToDirectoryInput = findViewById(R.id.save_to_path_input);
        imageButton = findViewById(R.id.imageButton);

        Button resetDeviceNameButton = findViewById(R.id.device_name_reset_button);
        Button saveToDirectoryPickerButton = findViewById(R.id.save_to_path_picker_button);
        Button resetSavePathButton = findViewById(R.id.save_to_path_reset_button);
        Button submitButton = findViewById(R.id.submit_button);
        Button mainMenuButton = findViewById(R.id.main_menu_button);
        Button btnCredits = findViewById(R.id.btn_credits);

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
                Log.e("PreferencesActivity", "Error loading preferences", e);
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
                Log.e("PreferencesActivity", "Failed to create media directory");
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
                Log.d("PreferencesActivity", "Read JSON from file: " + jsonString.toString());
                return jsonString.toString();
            } catch (Exception e) {
                Log.e("PreferencesActivity", "Error reading JSON from file", e);
            }
        } else {
            Log.d("PreferencesActivity", "File does not exist: " + file.getAbsolutePath());
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
        Log.d("PreferencesActivity", "Save to path: " + saveToDirectory);

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
            Toast.makeText(this, "Preferences updated", Toast.LENGTH_SHORT).show();
            Log.d("PreferencesActivity", "Preferences updated: " + configJson.toString());
        } catch (Exception e) {
            Log.e("PreferencesActivity", "Error creating JSON", e);
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
                Log.d("PreferencesActivity", "Config folder created: " + folder.getAbsolutePath());
                if (!folderCreated) {
                    Log.e("PreferencesActivity", "Failed to create config folder");
                    return;
                }
            }

            File file = new File(folder, CONFIG_FILE_NAME);
            FileOutputStream fileOutputStream = new FileOutputStream(file);
            fileOutputStream.write(jsonString.getBytes());
            fileOutputStream.close();
            Log.d("PreferencesActivity", "Preferences saved: " + jsonString);
            Log.d("PreferencesActivity", "Preferences saved at: " + file.getAbsolutePath());
        } catch (Exception e) {
            Log.e("PreferencesActivity", "Error saving JSON to file", e);
        }
    }

    private void goToMainMenu() {
        // Navigate back to the main screen
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