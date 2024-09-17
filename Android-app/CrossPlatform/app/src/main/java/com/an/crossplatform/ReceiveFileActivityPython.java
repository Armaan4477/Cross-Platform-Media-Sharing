package com.an.crossplatform;

import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import org.json.JSONException;
import org.json.JSONObject;

public class ReceiveFileActivityPython extends AppCompatActivity {

    private String senderJson;
    private String deviceName;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiting_to_receive);

        // Retrieve senderJson from the intent
        senderJson = getIntent().getStringExtra("receiverJson");
        Log.d("ReceiveFileActivityPython", "Received JSON: " + senderJson);

        // Parse the JSON to extract the device name
        try {
            JSONObject jsonObject = new JSONObject(senderJson);
            deviceName = jsonObject.optString("device_name", "Unknown Device");  // Default to "Unknown Device" if not found
        } catch (JSONException e) {
            Log.e("ReceiveFileActivityPython", "Failed to parse senderJson", e);
            deviceName = "Unknown Device";  // Fallback in case of error
        }

        // Update the TextView with the message
        TextView txt_waiting = findViewById(R.id.txt_waiting);
        txt_waiting.setText("Waiting to receive file from " + deviceName);
    }
}
