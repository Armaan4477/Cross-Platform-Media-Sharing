package com.an.crossplatform;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Button btnSend = findViewById(R.id.btn_send);
        Button btnReceive = findViewById(R.id.btn_receive);
        ImageButton btn_preferences = findViewById(R.id.btn_preferences);

        btnSend.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, DiscoverDevicesActivity.class);
            startActivity(intent);
        });

        btnReceive.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, WaitingToReceiveActivity.class);
            startActivity(intent);
        });

        btn_preferences.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, PreferencesActivity.class);
            startActivity(intent);
        });
    }
}

