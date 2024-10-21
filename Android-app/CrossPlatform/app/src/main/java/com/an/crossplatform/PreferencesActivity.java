package com.an.crossplatform;

import android.content.Intent;
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
    private EditText saveToPathInput;
    private Map<String, Object> originalPreferences = new HashMap<>();

    private static final String CONFIG_FOLDER_NAME = "config";
    private static final String CONFIG_FILE_NAME = "config.json";  // Config file stored in internal storage
    private ImageButton imageButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_preferences);

        deviceNameInput = findViewById(R.id.device_name_input);
        saveToPathInput = findViewById(R.id.save_to_path_input);
        imageButton = findViewById(R.id.imageButton);

        Button resetDeviceNameButton = findViewById(R.id.device_name_reset_button);
        Button saveToPathPickerButton = findViewById(R.id.save_to_path_picker_button);
        Button resetSavePathButton = findViewById(R.id.save_to_path_reset_button);
        Button submitButton = findViewById(R.id.submit_button);
        Button mainMenuButton = findViewById(R.id.main_menu_button);
        Button btnCredits = findViewById(R.id.btn_credits);

        // Load saved preferences from internal storage
        loadPreferences();

        resetDeviceNameButton.setOnClickListener(v -> resetDeviceName());
        saveToPathPickerButton.setOnClickListener(v -> pickDirectory());
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
                // Parse the JSON to get the preferences
                JSONObject configJson = new JSONObject(jsonString);
                String deviceName = configJson.optString("device_name", "Android Device");
                String saveToPath = configJson.optString("save_to_directory", Environment.getExternalStorageDirectory().getPath());

                // Store original preferences in a map
                originalPreferences.put("device_name", deviceName);
                originalPreferences.put("save_to_directory", saveToPath);

                // Set the input fields with the retrieved values
                deviceNameInput.setText(deviceName);
                saveToPathInput.setText(saveToPath);
            } catch (Exception e) {
                Log.e("PreferencesActivity", "Error loading preferences", e);
                setDefaults();  // Fallback to default values if any error occurs
            }
        } else {
            setDefaults();  // Use default values if the file doesn't exist
        }
    }

    private void setDefaults() {
        // In case of an error, use defaults
        originalPreferences.put("device_name", "Android Device");
        originalPreferences.put("save_to_directory", Environment.getExternalStorageDirectory().getPath());

        deviceNameInput.setText("Android Device");
        saveToPathInput.setText(Environment.getExternalStorageDirectory().getPath());
    }

    // Method to read JSON from internal storage
    private String readJsonFromFile() {
        // Get the internal file path for the config directory
        File folder = new File(getFilesDir(), CONFIG_FOLDER_NAME);  // Internal storage file path
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
        // Set the saveToPath to the Android/media folder within external storage
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
        String saveToPath = mediaDir.getAbsolutePath();

        // Remove the "/storage/emulated/0" prefix if it exists
        if (saveToPath.startsWith("/storage/emulated/0")) {
            saveToPath = saveToPath.replace("/storage/emulated/0", ""); // Remove the prefix
        }
        saveToPathInput.setText(saveToPath);  // Reset save path to default
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
                            String pickedDir = result.getData().getData().getPath();
                            saveToPathInput.setText(pickedDir);
                        }
                    });

    private void submitPreferences() {
        String deviceName = deviceNameInput.getText().toString();
        String saveToPathURI = saveToPathInput.getText().toString();
        // Convert into a path like /storage/emulated/0/Download
        String saveToPath = saveToPathURI.substring(saveToPathURI.indexOf(":", 0) + 1);
        Log.d("PreferencesActivity", "Save to path: " + saveToPath);

        if (deviceName.isEmpty()) {
            Toast.makeText(this, "Device Name cannot be empty", Toast.LENGTH_SHORT).show();
            return;
        }

        // Create a new JSON object with the updated preferences
        JSONObject configJson = new JSONObject();
        try {
            configJson.put("device_name", deviceName);
            configJson.put("save_to_directory", saveToPath);
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
            File folder = new File(getFilesDir(),CONFIG_FOLDER_NAME);  // Ensure the config folder exists
            if (!folder.exists()) {
                boolean folderCreated = folder.mkdir();
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