package com.an.crossplatform;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import com.an.crossplatform.R;

public class CreditsActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.credits); // Set your layout

        // Set up links for each person
        setupLinkButtons();

        // Close button functionality
        Button closeButton = findViewById(R.id.close_button);
        closeButton.setOnClickListener(v -> finish()); // Close activity
    }

    private void setupLinkButtons() {
        // Armaan's links
        Button armaanGitHubButton = findViewById(R.id.armaan_github_button);
        armaanGitHubButton.setOnClickListener(v -> openLink("https://github.com/Armaan4477"));

        Button armaanLinkedInButton = findViewById(R.id.armaan_linkedin_button);
        armaanLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/armaan-nakhuda-756492235/"));

        // Nishal's links
        Button nishalGitHubButton = findViewById(R.id.nishal_github_button);
        nishalGitHubButton.setOnClickListener(v -> openLink("https://github.com/Ailover123"));

        Button nishalLinkedInButton = findViewById(R.id.nishal_linkedin_button);
        nishalLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/nishal-poojary-159530290"));

        // Samay's links
        Button samayGitHubButton = findViewById(R.id.samay_github_button);
        samayGitHubButton.setOnClickListener(v -> openLink("https://github.com/ChampionSamay1644"));

        Button samayLinkedInButton = findViewById(R.id.samay_linkedin_button);
        samayLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/samaypandey1644"));

        // Urmi's links
        Button urmiGitHubButton = findViewById(R.id.urmi_github_button);
        urmiGitHubButton.setOnClickListener(v -> openLink("https://github.com/ura-dev04"));

        Button urmiLinkedInButton = findViewById(R.id.urmi_linkedin_button);
        urmiLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/urmi-joshi-6697a7320/"));

        // Yash's links
        Button yashGitHubButton = findViewById(R.id.yash_github_button);
        yashGitHubButton.setOnClickListener(v -> openLink("https://github.com/FrosT2k5"));

        Button yashLinkedInButton = findViewById(R.id.yash_linkedin_button);
        yashLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/yash-patil-385171257"));

        // Adwait's links
        Button adwaitGitHubButton = findViewById(R.id.adwait_github_button);
        adwaitGitHubButton.setOnClickListener(v -> openLink("https://github.com/Adwait0901"));

        Button adwaitLinkedInButton = findViewById(R.id.adwait_linkedin_button);
        adwaitLinkedInButton.setOnClickListener(v -> openLink("https://www.linkedin.com/in/adwait-patil-56a1682a9/"));

    }

    private void openLink(String url) {
        Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        startActivity(browserIntent);
    }
}
