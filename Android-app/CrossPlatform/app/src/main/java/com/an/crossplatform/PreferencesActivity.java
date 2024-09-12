package com.an.crossplatform;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.View;
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
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;

public class PreferencesActivity extends AppCompatActivity {

    private EditText deviceNameInput;
    private EditText saveToPathInput;
    private Map<String, Object> originalPreferences = new HashMap<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_preferences);

        deviceNameInput = findViewById(R.id.device_name_input);
        saveToPathInput = findViewById(R.id.save_to_path_input);

        Button resetDeviceNameButton = findViewById(R.id.device_name_reset_button);
        Button saveToPathPickerButton = findViewById(R.id.save_to_path_picker_button);
        Button resetSavePathButton = findViewById(R.id.save_to_path_reset_button);
        Button submitButton = findViewById(R.id.submit_button);
        Button mainMenuButton = findViewById(R.id.main_menu_button);

        // Load saved preferences
        loadPreferences();

        resetDeviceNameButton.setOnClickListener(v -> resetDeviceName());

        saveToPathPickerButton.setOnClickListener(v -> pickDirectory());

        resetSavePathButton.setOnClickListener(v -> resetSavePath());

        submitButton.setOnClickListener(v -> submitPreferences());

        mainMenuButton.setOnClickListener(v -> goToMainMenu());
    }

    private void loadPreferences() {
        String jsonString = readJsonFromFile();  // Check internal storage first

        if (jsonString == null) {
            jsonString = readRawJsonFile(R.raw.config);  // Fallback to raw folder
        }

        try {
            // Parse the JSON to get the preferences
            JSONObject configJson = new JSONObject(jsonString);
            String deviceName = configJson.getString("device_name");
            String saveToPath = configJson.getString("save_to_directory");

            // Store original preferences in a map
            originalPreferences.put("device_name", deviceName);
            originalPreferences.put("save_to_directory", saveToPath);

            // Set the input fields with the retrieved values
            deviceNameInput.setText(deviceName);
            saveToPathInput.setText(saveToPath);

        } catch (Exception e) {
            Log.e("PreferencesActivity", "Error loading preferences", e);
            // In case of an error, use defaults
            originalPreferences.put("device_name", "Android Device");
            originalPreferences.put("save_to_directory", Environment.getExternalStorageDirectory().getPath());

            deviceNameInput.setText("Android Device");
            saveToPathInput.setText(Environment.getExternalStorageDirectory().getPath());
        }
    }

    // Method to read JSON from internal storage if it exists
    private String readJsonFromFile() {
        File file = new File(getFilesDir(), "config.json");
        if (file.exists()) {
            StringBuilder jsonString = new StringBuilder();
            try {
                BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file)));
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                reader.close();
                return jsonString.toString();
            } catch (Exception e) {
                Log.e("PreferencesActivity", "Error reading JSON from file", e);
            }
        }
        return null;
    }


    private void resetDeviceName() {
        deviceNameInput.setText(android.os.Build.MODEL);
    }

    private void resetSavePath() {
        saveToPathInput.setText(Environment.getExternalStorageDirectory().getPath());
    }

    private void pickDirectory() {
        // Launch a directory picker (using built-in Android picker)
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
        String saveToPath = saveToPathInput.getText().toString();

        if (deviceName.isEmpty()) {
            Toast.makeText(this, "Device Name cannot be empty", Toast.LENGTH_SHORT).show();
            return;
        }

        // Save preferences by updating the config.json file from raw folder
        String jsonString = readRawJsonFile(R.raw.config);
        jsonString = jsonString.replace("\"device_name\": \"Android Device\"",
                "\"device_name\": \"" + deviceName + "\"");
        jsonString = jsonString.replace("\"save_to_directory\": \"/tree/primary/Download\"",
                "\"save_to_directory\": \"" + saveToPath + "\"");
        saveJsonToFile(jsonString);

        // Compare and show a message
        if (!deviceName.equals(originalPreferences.get("device_name")) ||
                !saveToPath.equals(originalPreferences.get("save_to_directory"))) {
            Toast.makeText(this, "Preferences updated", Toast.LENGTH_SHORT).show();
            Log.d("PreferencesActivity", "Preferences updated");
            Log.d("PreferencesActivity", "Device Name: " + deviceName);
            Log.d("PreferencesActivity", "Save To Path: " + saveToPath);
        } else {
            Toast.makeText(this, "No changes detected", Toast.LENGTH_SHORT).show();
        }
    }

    private String readRawJsonFile(int rawResourceId) {
        // First try to read the JSON file from internal storage
        try {
            File file = new File(getFilesDir(), "config.json");
            if (file.exists()) {
                InputStream inputStream = new FileInputStream(file);
                BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
                StringBuilder jsonString = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                reader.close();
                inputStream.close();
                return jsonString.toString();
            }
        } catch (Exception ignored) {
            StringBuilder jsonString = new StringBuilder();
            try {
                InputStream inputStream = getResources().openRawResource(rawResourceId);
                BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonString.append(line);
                }
                reader.close();
                inputStream.close();
            } catch (Exception e) {
                Log.e("PreferencesActivity", "Error reading raw JSON file", e);
            }
            return jsonString.toString();
        }
        return "";
    }

    // Method to save the modified JSON to internal storage
    private void saveJsonToFile(String jsonString) {
        try {
            File file = new File(getFilesDir(), "config.json");
            FileOutputStream outputStream = new FileOutputStream(file);
            outputStream.write(jsonString.getBytes());
            outputStream.close();
        } catch (Exception e) {
            Log.e("PreferencesActivity", "Error saving JSON to file", e);
        }
    }

    private void goToMainMenu() {
        finish();  // Navigate back to the main menu
    }
}