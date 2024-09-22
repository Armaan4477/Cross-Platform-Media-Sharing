package com.an.crossplatform;

import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONException;
import org.json.JSONObject;

public class ReceiveFileActivity extends AppCompatActivity {

    private String senderJson;
    private String deviceName;
    private String osType;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        // Retrieve senderJson from the intent
        senderJson = getIntent().getStringExtra("receiverJson");
        Log.d("ReceiveFileActivityPython", "Received JSON: " + senderJson);

        // Retrieve the JSON string from the intent
        senderJson = getIntent().getStringExtra("receivedJson");
        // Retrieve the OS type from the string with try catch block
        try {
            osType = new JSONObject(senderJson).getString("os");
            deviceName = new JSONObject(senderJson).getString("device_name");
        } catch (Exception e) {
            Log.e("SendFileActivity", "Failed to retrieve OS type", e);
        }
        Log.d("SendFileActivity", "Received JSON: " + senderJson);
        Log.d("SendFileActivity", "OS Type: " + osType);

        // Update the TextView with the message
        TextView txt_waiting = findViewById(R.id.txt_waiting);
        txt_waiting.setText("Waiting to receive file from " + deviceName);
    }
}
