package com.an.crossplatform;
import android.app.Dialog;
import android.content.Context;
import android.os.Bundle;
import android.view.Window;
import android.widget.TextView;
import android.widget.ImageButton;

public class HelpDialog extends Dialog {

    public HelpDialog(Context context) {
        super(context);
    }

    private ImageButton closeButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.help_activity);  // Use the help_activity.xml layout
        closeButton = findViewById(R.id.close_button);
        closeButton.setOnClickListener(v -> dismiss());

}}
