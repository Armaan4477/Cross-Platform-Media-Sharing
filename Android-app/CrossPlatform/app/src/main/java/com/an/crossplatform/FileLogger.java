package com.an.crossplatform;

import android.content.Context;
import android.os.Environment;
import android.util.Log;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class FileLogger {
    private static File logFile;
    private static Context appContext;

    public static void init(Context context) {
        try {
            appContext = context.getApplicationContext();
            File mediaDir = new File(Environment.getExternalStorageDirectory(), "Android/media/" + appContext.getPackageName() + "/Logs");
            if (!mediaDir.exists()) {
                boolean created = mediaDir.mkdirs();
                if (!created) {
                    Log.e("FileLogger", "Failed to create DataDash directory");
                    return;
                }
            }
            logFile = new File(mediaDir, "log.txt");
            if (!logFile.exists()) {
                boolean created = logFile.createNewFile();
                if (!created) {
                    Log.e("FileLogger", "Failed to create log file");
                }
            }
        } catch (IOException e) {
            Log.e("FileLogger", "Error initializing logger", e);
        }
    }

    private static void ensureInitialized() {
        if (logFile == null || !logFile.exists()) {
            Log.e("FileLogger", "Logger not properly initialized");
            return;
        }
    }

    public static void log(String tag, String message) {
        ensureInitialized();
        Log.d(tag, message);
        writeToFile(tag, message, null);
    }

    public static void log(String tag, String message, Throwable throwable) {
        ensureInitialized();
        Log.e(tag, message, throwable);
        writeToFile(tag, message, throwable);
    }

    private static void writeToFile(String tag, String message, Throwable throwable) {
        if (logFile == null) return;

        try (FileWriter writer = new FileWriter(logFile, true)) {
            String timeStamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date());
            writer.append(timeStamp)
                    .append(" ")
                    .append(tag)
                    .append(": ")
                    .append(message)
                    .append("\n");

            if (throwable != null) {
                StringWriter sw = new StringWriter();
                throwable.printStackTrace(new PrintWriter(sw));
                writer.append(sw.toString())
                        .append("\n");
            }
        } catch (IOException e) {
            Log.e("FileLogger", "Error writing to log file", e);
        }
    }
}