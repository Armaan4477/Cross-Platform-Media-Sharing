package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

public class CreditsActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.credits);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                closeBtn();
            }
        });

        // Set up links for each person
        setupLinkButtons();

        // Close button functionality
        Button closeButton = findViewById(R.id.close_button);
        closeButton.setOnClickListener(v -> closeBtn());
    }

    private void setupLinkButtons() {
        // Armaan's links
        Button armaanGitHubButton = findViewById(R.id.armaan_github_button);
        armaanGitHubButton.setOnClickListener(v -> openLink("https://github.com/Armaan4477"));

        Button armaanLinkedInButton = findViewById(R.id.armaan_linkedin_button);
        armaanLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/armaan-nakhuda-756492235/"));

        // Samay's links
        Button samayGitHubButton = findViewById(R.id.samay_github_button);
        samayGitHubButton.setOnClickListener(v -> openLink("https://github.com/ChampionSamay1644"));

        Button samayLinkedInButton = findViewById(R.id.samay_linkedin_button);
        samayLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/samaypandey1644"));

        // Yash's links
        Button yashGitHubButton = findViewById(R.id.yash_github_button);
        yashGitHubButton.setOnClickListener(v -> openLink("https://github.com/FrosT2k5"));

        Button yashLinkedInButton = findViewById(R.id.yash_linkedin_button);
        yashLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/yash-patil-385171257"));

        // Aarya's links
        Button aaryaGitHubButton = findViewById(R.id.aarya_github_button);
        aaryaGitHubButton.setOnClickListener(v -> openLink("https://github.com/aaryaa28"));

        Button aaryaLinkedInButton = findViewById(R.id.aarya_linkedin_button);
        aaryaLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/aarya-walve-10259325b/"));
    }

    private void openLink(String url) {
        Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        startActivity(browserIntent);
    }

    private void closeBtn() {
        finish();
    }
}