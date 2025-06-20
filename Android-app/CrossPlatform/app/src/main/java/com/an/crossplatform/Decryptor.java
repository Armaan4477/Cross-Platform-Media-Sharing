package com.an.crossplatform;

import android.content.Intent;
import android.os.Bundle;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.TableLayout;
import android.widget.TableRow;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.an.crossplatform.AESUtils.EncryptionUtils;

import java.io.File;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class Decryptor extends AppCompatActivity {

    private ArrayList<String> encryptedFiles;
    private EditText passwordInput;
    private Button decryptButton;
    private TableLayout tableLayout;
    private int incorrectPasswordAttempts = 0;
    private ExecutorService executorService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_decryptor);

        Intent intent = getIntent();
        encryptedFiles = intent.getStringArrayListExtra("files");

        passwordInput = findViewById(R.id.editTextText2);
        decryptButton = findViewById(R.id.button);
        tableLayout = findViewById(R.id.tableLayout);

        decryptButton.setOnClickListener(v -> {
            String password = passwordInput.getText().toString();
            if (password.isEmpty()) {
                Toast.makeText(this, "Please enter a password.", Toast.LENGTH_SHORT).show();
                return;
            }
            decryptButton.setEnabled(false); // Disable the button to prevent spamming
            decryptFilesInBackground(password);
        });
    }

    private void decryptFilesInBackground(String password) {
        executorService = Executors.newSingleThreadExecutor();
        executorService.execute(() -> {
            runOnUiThread(() -> Toast.makeText(Decryptor.this, "Decryption started...", Toast.LENGTH_SHORT).show());
            decryptFiles(password);
        });
    }

    private void decryptFiles(String password) {
        boolean allDecryptedSuccessfully = true;
        boolean shouldStopDecryption = false;

        for (String filePath : encryptedFiles) {
            if (shouldStopDecryption) break;

            File inputFile = new File(filePath);
            if (inputFile.isDirectory()) continue;

            String outputFileName = filePath.substring(0, filePath.length() - 6);
            File outputFile = new File(inputFile.getParent(), new File(outputFileName).getName());

            runOnUiThread(() -> addFileRow(filePath));

            try {
                EncryptionUtils.decryptFile(password, inputFile, outputFile);

                runOnUiThread(() -> updateProgress(filePath, 100));

            } catch (Exception e) {
                allDecryptedSuccessfully = false;
                incorrectPasswordAttempts++;

                if (outputFile.exists()) {
                    outputFile.delete();
                }

                if (incorrectPasswordAttempts >= 3) {
                    runOnUiThread(() -> {
                        Toast.makeText(this, "Password incorrect multiple times. Deleting encrypted files.", Toast.LENGTH_LONG).show();
                    });
                    deleteAllFiles();
                    shouldStopDecryption = true;
                    break;
                }

                runOnUiThread(() -> {
                    Toast.makeText(this, "Incorrect Password, Remaining attempts: " + (3 - incorrectPasswordAttempts), Toast.LENGTH_LONG).show();
                });
                // Enable the button to allow the user to try again and clear the password field and table layout
                runOnUiThread(() -> {
                    decryptButton.setEnabled(true);
                    passwordInput.setText("");
                    tableLayout.removeAllViews();
                });
                e.printStackTrace();
                break;
            }
        }

        if (allDecryptedSuccessfully) {
            runOnUiThread(() -> {
                Toast.makeText(this, "All files decrypted successfully!", Toast.LENGTH_SHORT).show();
            });
            deleteEncryptedFiles();
        }
    }

    private void addFileRow(String filePath) {
        TableRow tableRow = new TableRow(this);
        TextView filePathTextView = new TextView(this);
        filePathTextView.setText(filePath);
        filePathTextView.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 0.8f));

        ProgressBar progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setLayoutParams(new TableRow.LayoutParams(0, TableRow.LayoutParams.WRAP_CONTENT, 0.2f));
        progressBar.setProgress(0);
        progressBar.setTag(filePath);

        tableRow.addView(filePathTextView);
        tableRow.addView(progressBar);
        tableLayout.addView(tableRow);
    }

    private void updateProgress(String filePath, int progress) {
        for (int i = 0; i < tableLayout.getChildCount(); i++) {
            TableRow row = (TableRow) tableLayout.getChildAt(i);
            ProgressBar progressBar = (ProgressBar) row.getChildAt(1);
            if (filePath.equals(progressBar.getTag())) {
                progressBar.setProgress(progress);
                break;
            }
        }
    }

    private void deleteEncryptedFiles() {
        for (String filePath : encryptedFiles) {
            File inputFile = new File(filePath);
            if (inputFile.exists()) {
                inputFile.delete();
            }
        }

        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }

        runOnUiThread(() -> {
            TransferCompleteActivity transferCompleteActivity = new TransferCompleteActivity(Decryptor.this);
            transferCompleteActivity.requestWindowFeature(Window.FEATURE_NO_TITLE);
            transferCompleteActivity.show();
        });
    }

    private void deleteAllFiles() {
        for (String filePath : encryptedFiles) {
            File inputFile = new File(filePath);
            if (inputFile.exists()) {
                deleteRecursive(inputFile);
            }
        }

        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }

        runOnUiThread(() -> {
            TransferCompleteActivity transferCompleteActivity = new TransferCompleteActivity(Decryptor.this);
            transferCompleteActivity.requestWindowFeature(Window.FEATURE_NO_TITLE);
            transferCompleteActivity.show();
        });
    }

    private void deleteRecursive(File fileOrDir) {
        if (fileOrDir.isDirectory()) {
            File[] children = fileOrDir.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteRecursive(child);
                }
            }
        }
        fileOrDir.delete();
    }
}