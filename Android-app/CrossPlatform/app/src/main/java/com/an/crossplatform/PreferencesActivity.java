package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.View;
import android.view.Window;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.Switch;
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

import android.app.DownloadManager;
import android.content.Context;



public class PreferencesActivity extends AppCompatActivity {

    private EditText deviceNameInput;
    private EditText saveToDirectoryInput;
    private Map<String, Object> originalPreferences = new HashMap<>();

    private static final String CONFIG_FOLDER_NAME = "config";
    private static final String CONFIG_FILE_NAME = "config.json";
    private ImageButton imageButton;
    private Switch encryptionSwitch;
    private Switch warningsSwitch;
    private Switch autoCheckSwitch;
    private Spinner updateChannelSpinner;
    private boolean isInitialLoad = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_preferences);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                toastdis();
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
        encryptionSwitch = findViewById(R.id.encryption_switch);
        warningsSwitch = findViewById(R.id.show_warnings_switch);
        autoCheckSwitch = findViewById(R.id.auto_check_updates_switch);

        updateChannelSpinner = findViewById(R.id.update_channel_spinner);
        ArrayAdapter<CharSequence> adapter = ArrayAdapter.createFromResource(this,
                R.array.update_channels, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        updateChannelSpinner.setAdapter(adapter);

        // Set initial value from config
        String savedChannel = getSavedUpdateChannel();
        updateChannelSpinner.setSelection(savedChannel.equals("beta") ? 1 : 0);

        updateChannelSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                String selectedChannel = position == 0 ? "stable" : "beta";
                updateChannelInConfig(selectedChannel);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        // Set the app version
        TextView appVersionLabel = findViewById(R.id.app_version_label);
        appVersionLabel.setText("App Version: " + getVersionName());

        loadPreferences();

        resetDeviceNameButton.setOnClickListener(v -> resetDeviceName());
        saveToDirectoryPickerButton.setOnClickListener(v -> pickDirectory());
        resetSavePathButton.setOnClickListener(v -> resetSavePath());
        submitButton.setOnClickListener(v -> submitPreferences());
        mainMenuButton.setOnClickListener(v -> toastdis());
        imageButton.setOnClickListener(v -> openHelpMenu());
        btnCredits.setOnClickListener(v -> {
            Intent intent = new Intent(PreferencesActivity.this, CreditsActivity.class);
            startActivity(intent);
        });

        String versionName = getVersionName();

        Button checkForUpdateButton = findViewById(R.id.check_for_update_button);
        checkForUpdateButton.setOnClickListener(v -> checkForUpdates());
    }

    private String getSavedUpdateChannel() {
        try {
            String jsonString = readJsonFromFile();
            if (jsonString != null) {
                JSONObject config = new JSONObject(jsonString);
                return config.optString("update_channel", "stable");
            }
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error reading update channel", e);
        }
        return "stable";
    }

    private void updateChannelInConfig(String channel) {
        try {
            String jsonString = readJsonFromFile();
            JSONObject config = jsonString != null ?
                    new JSONObject(jsonString) : new JSONObject();

            config.put("update_channel", channel);
            saveJsonToFile(config.toString());

            if (!isInitialLoad) {
                Toast.makeText(this, "Update channel changed to " + channel,
                        Toast.LENGTH_SHORT).show();
            }
            isInitialLoad = false;
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error updating channel", e);
        }
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

    private void checkForUpdates() {
        String channel = loadchannel();
        FileLogger.log("CheckForUpdates", "Checking for updates on Update channel: " + channel);

        new Thread(() -> {
            String apiVersion = null;
            HttpURLConnection connection = null;

            try {
                URL url;
                if (channel.equals("beta")) {
                    url = new URL("https://datadashshare.vercel.app/api/platformNumberbeta?platform=android");
                } else {
                    url = new URL("https://datadashshare.vercel.app/api/platformNumber?platform=android");
                }

                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");

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
                } else {
                    FileLogger.log("CheckForUpdates", "Failed to fetch version, Response Code: " + responseCode);
                }
            } catch (Exception e) {
                FileLogger.log("CheckForUpdates", "Error fetching updates", e);
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }

            String finalApiVersion = apiVersion;
            new Handler(Looper.getMainLooper()).post(() -> processVersionCheckResult(finalApiVersion));
        }).start();
    }

    private void processVersionCheckResult(String apiVersion) {
        if (apiVersion != null) {
            try {
                String appVersion = getVersionName();
                String channel = loadchannel();

                int[] apiNums = convertVersionToNumbers(apiVersion);
                int[] appNums = convertVersionToNumbers(appVersion);

                int comparison = compareVersions(appNums, apiNums);

                if (comparison < 0) {
                    showMessageDialog("Update Available",
                            "Your app version " + appVersion + " is outdated. Latest version is " + apiVersion,
                            true,
                            channel);
                } else if (comparison > 0) {
                    showMessageDialog("Development Version",
                            "Your app version " + appVersion + " is newer than the released version " + apiVersion,
                            true,
                            channel);
                } else {
                    showMessageDialog("Up to Date",
                            "Your app is running the latest version " + appVersion,
                            false,
                            channel);
                }

            } catch (Exception e) {
                FileLogger.log("CheckForUpdates", "Error comparing versions", e);
                showMessageDialog("Error", "Error checking for updates.", false, "stable");
            }
        } else {
            showMessageDialog("Error", "Failed to check for updates.", false, "stable");
        }
    }

    private int[] convertVersionToNumbers(String version) {
        String[] parts = version.split("\\.");
        int[] numbers = new int[3];

        for (int i = 0; i < parts.length && i < 3; i++) {
            try {
                numbers[i] = Integer.parseInt(parts[i]);
            } catch (NumberFormatException e) {
                numbers[i] = 0;
            }
        }

        return numbers;
    }

    private int compareVersions(int[] version1, int[] version2) {
        for (int i = 0; i < 3; i++) {
            if (version1[i] != version2[i]) {
                return Integer.compare(version1[i], version2[i]);
            }
        }
        return 0;
    }

    private void showMessageDialog(String title, String message, boolean showDownloadsButton, String channel) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle(title)
                .setMessage(message)
                .setPositiveButton("Close", (dialog, which) -> dialog.dismiss());

        if (showDownloadsButton) {
            String buttonText = channel.equals("beta") ? "Open Beta Page" : "Open Downloads Page";
            String url = channel.equals("beta") ?
                    "https://datadash.is-a.dev/beta" :
                    "https://datadash.is-a.dev/download";

            builder.setNegativeButton(buttonText, (dialog, which) -> {
                Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                startActivity(browserIntent);
            });

            String apiVersion = message.substring(message.lastIndexOf(" ") + 1);
            builder.setNeutralButton("Download Latest Version", (dialog, which) -> {
                downloadLatestVersion(apiVersion, channel);
            });
        }

        AlertDialog dialog = builder.create();
        dialog.show();
    }

    private void downloadLatestVersion(String version, String channel) {
        try {
            String downloadUrl;
            String fileNameSuffix;

            if (channel.equals("beta")) {
                downloadUrl = "https://github.com/Project-Bois/data-dash-test-files/raw/refs/heads/main/DataDash(android).apk";
                fileNameSuffix = "_beta";
            } else {
                downloadUrl = "https://github.com/Project-Bois/DataDash-files/raw/refs/heads/main/DataDash(android).apk";
                fileNameSuffix = "";
            }

            String fileName = "DataDash_v" + version + fileNameSuffix + ".apk";

            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(downloadUrl));
            request.setTitle("DataDash Update v" + version + (channel.equals("beta") ? " Beta" : ""));
            request.setDescription("Downloading version " + version);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);

            request.setDestinationInExternalPublicDir(
                    Environment.DIRECTORY_DOWNLOADS,
                    "DataDash/" + fileName
            );

            DownloadManager downloadManager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            if (downloadManager != null) {
                long downloadId = downloadManager.enqueue(request);
                Toast.makeText(this, "Downloading DataDash v" + version + (channel.equals("beta") ? " Beta" : ""), Toast.LENGTH_LONG).show();
                FileLogger.log("PreferencesActivity", "Started download of version " + version + " (" + channel + ")");
            }
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error starting download", e);
            Toast.makeText(this, "Error starting download: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void loadPreferences() {
        String jsonString = readJsonFromFile();

        if (jsonString != null) {
            try {
                JSONObject configJson = new JSONObject(jsonString);
                String deviceName = configJson.getString("device_name");
                String saveToDirectory = configJson.getString("saveToDirectory");
                boolean encryption = configJson.getBoolean("encryption");
                boolean show_warn = configJson.getBoolean("show_warn");
                boolean auto_check = configJson.getBoolean("auto_check");

                // Store original preferences in a map
                originalPreferences.put("device_name", deviceName);
                originalPreferences.put("saveToDirectory", saveToDirectory);
                originalPreferences.put("encryption", encryption);
                originalPreferences.put("show_warn", show_warn);
                originalPreferences.put("auto_check", auto_check);

                // Set the input fields with the retrieved values
                deviceNameInput.setText(deviceName);
                saveToDirectoryInput.setText(saveToDirectory);
                encryptionSwitch.setChecked(encryption);
                warningsSwitch.setChecked(show_warn);
                autoCheckSwitch.setChecked(auto_check);

            } catch (Exception e) {
                FileLogger.log("PreferencesActivity", "Error loading preferences", e);
                setDefaults();
            }
        } else {
            setDefaults();
        }
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

    private void setDefaults() {
        File mediaDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Media/");

        if (!mediaDir.exists()) {
            boolean dirCreated = mediaDir.mkdirs();
            if (!dirCreated) {
                FileLogger.log("PreferencesActivity", "Failed to create media directory");
                return;
            }
        }

        String saveToDirectory = mediaDir.getAbsolutePath();

        originalPreferences.put("device_name", "Android Device");
        originalPreferences.put("saveToDirectory", saveToDirectory);

        deviceNameInput.setText("Android Device");
        saveToDirectoryInput.setText(saveToDirectory);
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

    private void resetDeviceName() {
        deviceNameInput.setText(android.os.Build.MODEL);
    }

    private void resetSavePath() {
        File mediaDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "DataDash");

        if (!mediaDir.exists()) {
            boolean dirCreated = mediaDir.mkdirs();
            if (!dirCreated) {
                FileLogger.log("MainActivity", "Failed to create media directory");
                return;
            }
        }
        String saveToDirectory = mediaDir.getAbsolutePath();

        if (saveToDirectory.startsWith("/storage/emulated/0")) {
            saveToDirectory = saveToDirectory.replace("/storage/emulated/0", "");
        }
        saveToDirectoryInput.setText(saveToDirectory);
    }

    private void pickDirectory() {
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

                            if (pickedDir.contains("Download")) {
                                Toast.makeText(this, "Warning: Selected directory is within the Download folder", Toast.LENGTH_SHORT).show();
                            }
                            saveToDirectoryInput.setText(pickedDir);
                        }
                    });

    private void submitPreferences() {
        String deviceName = deviceNameInput.getText().toString();
        String saveToDirectoryURI = saveToDirectoryInput.getText().toString();
        boolean encryption = encryptionSwitch.isChecked();
        boolean showWarnings = warningsSwitch.isChecked();
        boolean autoCheck = autoCheckSwitch.isChecked();

        if (!saveToDirectoryURI.startsWith("/")) {
            saveToDirectoryURI = "/" + saveToDirectoryURI;
        }
        if (!saveToDirectoryURI.endsWith("/")) {
            saveToDirectoryURI += "/";
        }

        String saveToDirectory = saveToDirectoryURI.substring(saveToDirectoryURI.indexOf(":", 0) + 1);
        FileLogger.log("PreferencesActivity", "Save to path: " + saveToDirectory);

        if (deviceName.isEmpty()) {
            Toast.makeText(this, "Device Name cannot be empty", Toast.LENGTH_SHORT).show();
            return;
        }

        if (hasPreferencesChanged(deviceName, saveToDirectory, encryption, showWarnings, autoCheck)) {
            updateSpecificPreferences(deviceName, saveToDirectory, encryption, showWarnings, autoCheck);
            Toast.makeText(this, "Settings updated", Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "No changes detected", Toast.LENGTH_SHORT).show();
        }

        goToMainMenu();
    }

    private boolean hasPreferencesChanged(String newDeviceName, String newSaveToDirectory,
                                          boolean newEncryption, boolean newShowWarnings, boolean newAutoCheck) {
        String originalDeviceName = (String) originalPreferences.get("device_name");
        String originalSaveToDirectory = (String) originalPreferences.get("saveToDirectory");
        boolean originalEncryption = (boolean) originalPreferences.getOrDefault("encryption", false);
        boolean originalShowWarnings = (boolean) originalPreferences.getOrDefault("show_warn", true);
        boolean originalAutoCheck = (boolean) originalPreferences.getOrDefault("auto_check", true);

        return !newDeviceName.equals(originalDeviceName) ||
                !newSaveToDirectory.equals(originalSaveToDirectory) ||
                newEncryption != originalEncryption ||
                newShowWarnings != originalShowWarnings ||
                newAutoCheck != originalAutoCheck;
    }

    private void updateSpecificPreferences(String deviceName, String saveToDirectory,
                                           boolean encryption, boolean showWarnings, boolean autoCheck) {
        try {
            String jsonString = readJsonFromFile();
            JSONObject existingConfig = jsonString != null ?
                    new JSONObject(jsonString) : new JSONObject();

            boolean updated = false;

            if (!deviceName.equals(originalPreferences.get("device_name"))) {
                existingConfig.put("device_name", deviceName);
                updated = true;
            }
            if (!saveToDirectory.equals(originalPreferences.get("saveToDirectory"))) {
                existingConfig.put("saveToDirectory", saveToDirectory);
                updated = true;
            }
            if (encryption != (boolean) originalPreferences.getOrDefault("encryption", false)) {
                existingConfig.put("encryption", encryption);
                updated = true;
            }
            if (showWarnings != (boolean) originalPreferences.getOrDefault("show_warn", true)) {
                existingConfig.put("show_warn", showWarnings);
                updated = true;
            }
            if (autoCheck != (boolean) originalPreferences.getOrDefault("auto_check", true)) {
                existingConfig.put("auto_check", autoCheck);
                updated = true;
            }

            if (updated) {
                saveJsonToFile(existingConfig.toString());
                originalPreferences.put("device_name", deviceName);
                originalPreferences.put("saveToDirectory", saveToDirectory);
                originalPreferences.put("encryption", encryption);
                originalPreferences.put("show_warn", showWarnings);
                originalPreferences.put("auto_check", autoCheck);
            }
        } catch (Exception e) {
            FileLogger.log("PreferencesActivity", "Error updating specific preferences", e);
        }
    }

    private void saveJsonToFile(String jsonString) {
        try {
            File folder = new File(Environment.getExternalStorageDirectory(), "Android/media/" + getPackageName() + "/Config");
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
        Intent mainIntent = new Intent(PreferencesActivity.this, MainActivity.class);
        mainIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(mainIntent);
        finish();
    }

    private void toastdis() {
        Toast.makeText(this, "Settings Changes Discarded", Toast.LENGTH_SHORT).show();
        Intent mainIntent = new Intent(PreferencesActivity.this, MainActivity.class);
        mainIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
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