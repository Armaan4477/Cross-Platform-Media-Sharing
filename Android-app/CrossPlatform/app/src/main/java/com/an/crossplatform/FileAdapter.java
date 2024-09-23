package com.an.crossplatform;

import android.net.Uri;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class FileAdapter extends RecyclerView.Adapter<FileAdapter.FileViewHolder> {

    private final List<String> fileList;

    public FileAdapter(List<String> fileList) {
        this.fileList = fileList;
    }

    @NonNull
    @Override
    public FileViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(android.R.layout.simple_list_item_1, parent, false);
        return new FileViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull FileViewHolder holder, int position) {
        String filePath = fileList.get(position);
        String fileName = getFileNameFromPath(filePath);
        holder.fileTextView.setText(fileName);
    }

    @Override
    public int getItemCount() {
        return fileList.size();
    }

    public static class FileViewHolder extends RecyclerView.ViewHolder {
        public TextView fileTextView;

        public FileViewHolder(@NonNull View itemView) {
            super(itemView);
            fileTextView = itemView.findViewById(android.R.id.text1);
        }
    }

    // Helper method to extract file name from URI or path
    private String getFileNameFromPath(String filePath) {
        Uri uri = Uri.parse(filePath);
        String lastSegment = uri.getLastPathSegment();

        if (!TextUtils.isEmpty(lastSegment)) {
            // Remove the prefix path and keep only the file name with extension
            int lastSlashIndex = lastSegment.lastIndexOf('/');
            if (lastSlashIndex != -1) {
                return lastSegment.substring(lastSlashIndex + 1);
            } else {
                return lastSegment;
            }
        }

        return "Unknown"; // Fallback in case the file name cannot be extracted
    }
}
