package com.an.crossplatform.AESUtils;

import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.SecretKeySpec;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.PBEKeySpec;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.KeySpec;

class KeyUtils {
    public static SecretKey getKeyFromPassword(String password, byte[] salt) throws NoSuchAlgorithmException, InvalidKeySpecException {

        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        KeySpec spec = new PBEKeySpec(password.toCharArray(), salt, 100000, 256);
        SecretKey secret = new SecretKeySpec(factory.generateSecret(spec)
                .getEncoded(), "AES");
        return secret;
    }

    public static IvParameterSpec generateIv() {
        byte[] iv = new byte[16];
        new SecureRandom().nextBytes(iv);
        return new IvParameterSpec(iv);
    }

    public static IvParameterSpec getIvFromBytes(byte[] bytes) {
        return new IvParameterSpec(bytes);
    }

    public static String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xFF & b);
            if (hex.length() == 1) {
                hexString.append('0'); // Pad with leading zero if necessary
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }
}

public class EncryptionUtils {
    public static void encryptFile(String password,
                                   File inputFile, File outputFile) throws NoSuchAlgorithmException, NoSuchPaddingException,
            InvalidKeyException, InvalidAlgorithmParameterException, IOException, IllegalBlockSizeException,
            BadPaddingException, InvalidKeySpecException {

        final String algorithm = "AES/CBC/PKCS5Padding";
        IvParameterSpec iv = KeyUtils.generateIv();
        byte[] salt = new byte[16];
        new SecureRandom().nextBytes(salt);

        SecretKey key = KeyUtils.getKeyFromPassword(password, salt);

        Cipher cipher = Cipher.getInstance(algorithm);
        cipher.init(Cipher.ENCRYPT_MODE, key, iv);
        FileInputStream inputStream = new FileInputStream(inputFile);
        FileOutputStream outputStream = new FileOutputStream(outputFile);
        byte[] buffer = new byte[64];

        byte[] encryptionHeader = new byte[32];
        System.arraycopy(salt, 0, encryptionHeader, 0, 16);
        System.arraycopy(iv.getIV(), 0, encryptionHeader, 16, 16);
        outputStream.write(encryptionHeader); // store salt and IV in first 32 bytes of file

        int bytesRead;

        while ((bytesRead = inputStream.read(buffer)) != -1) {
            byte[] output = cipher.update(buffer, 0, bytesRead);
            if (output != null) {
                outputStream.write(output);
            }
        }

        byte[] outputBytes = cipher.doFinal();
        if (outputBytes != null) {
            outputStream.write(outputBytes);
        }
        inputStream.close();
        outputStream.close();
    }

    public static void encryptFile(String password,
                                   FileInputStream inputStream, File outputFile) throws NoSuchAlgorithmException, NoSuchPaddingException,
            InvalidKeyException, InvalidAlgorithmParameterException, IOException, IllegalBlockSizeException,
            BadPaddingException, InvalidKeySpecException {

        final String algorithm = "AES/CBC/PKCS5Padding";
        IvParameterSpec iv = KeyUtils.generateIv();
        byte[] salt = new byte[16];
        new SecureRandom().nextBytes(salt);

        SecretKey key = KeyUtils.getKeyFromPassword(password, salt);

        Cipher cipher = Cipher.getInstance(algorithm);
        cipher.init(Cipher.ENCRYPT_MODE, key, iv);
        FileOutputStream outputStream = new FileOutputStream(outputFile);
        byte[] buffer = new byte[64];

        byte[] encryptionHeader = new byte[32];
        System.arraycopy(salt, 0, encryptionHeader, 0, 16);
        System.arraycopy(iv.getIV(), 0, encryptionHeader, 16, 16);
        outputStream.write(encryptionHeader); // store salt and IV in first 32 bytes of file

        int bytesRead;

        while ((bytesRead = inputStream.read(buffer)) != -1) {
            byte[] output = cipher.update(buffer, 0, bytesRead);
            if (output != null) {
                outputStream.write(output);
            }
        }

        byte[] outputBytes = cipher.doFinal();
        if (outputBytes != null) {
            outputStream.write(outputBytes);
        }
        inputStream.close();
        outputStream.close();
    }

    private static File handleFileConflict(File file) {
        if (!file.exists()) return file;

        String name = file.getName();
        String parent = file.getParent();
        String nameNoExt = name;
        String extension = "";

        int dotIndex = name.lastIndexOf('.');
        if (dotIndex > 0) {
            nameNoExt = name.substring(0, dotIndex);
            extension = name.substring(dotIndex);
        }

        int counter = 1;
        File newFile;
        do {
            newFile = new File(parent, nameNoExt + " (" + counter + ")" + extension);
            counter++;
        } while (newFile.exists());

        return newFile;
    }

    public static void decryptFile(String password,
                                   File inputFile, File outputFile) throws NoSuchAlgorithmException, NoSuchPaddingException,
            InvalidKeyException, InvalidAlgorithmParameterException, IOException, IllegalBlockSizeException,
            BadPaddingException, InvalidKeySpecException {

        final String algorithm = "AES/CBC/PKCS5Padding";
        
        // Handle file naming conflicts
        File finalOutputFile = handleFileConflict(outputFile);
        FileInputStream inputStream = new FileInputStream(inputFile);
        FileOutputStream outputStream = new FileOutputStream(finalOutputFile);

        byte[] salt = new byte[16];
        byte[] ivBytes = new byte[16];

        // Get salt and bytes from encryption header of file (first 32 bytes)
        inputStream.read(salt);
        inputStream.read(ivBytes);

        IvParameterSpec iv = KeyUtils.getIvFromBytes(ivBytes);

        SecretKey key = KeyUtils.getKeyFromPassword(password, salt);

        Cipher cipher = Cipher.getInstance(algorithm);
        cipher.init(Cipher.DECRYPT_MODE, key, iv);

        byte[] buffer = new byte[64];

        int bytesRead;

        while ((bytesRead = inputStream.read(buffer)) != -1) {
            byte[] output = cipher.update(buffer, 0, bytesRead);
            if (output != null) {
                outputStream.write(output);
            }
        }


        byte[] outputBytes = cipher.doFinal();
        if (outputBytes != null) {
            outputStream.write(outputBytes);
        }
        inputStream.close();
        outputStream.close();
    }
}