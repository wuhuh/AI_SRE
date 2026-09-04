package com.aisre.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@Service
public class AuthService {

    private final byte[] secret;

    public AuthService(@Value("${aisre.jwt.secret:dev-secret-change-me}") String secret) {
        this.secret = secret.getBytes(StandardCharsets.UTF_8);
    }

    public String issueToken(String username, String role) {
        long exp = Instant.now().getEpochSecond() + 3600;
        String header = base64Url("{\"alg\":\"HS256\",\"typ\":\"JWT\"}");
        String payload = base64Url("{\"sub\":\"" + username + "\",\"role\":\"" + role + "\",\"exp\":" + exp + "}");
        String signingInput = header + "." + payload;
        String signature = base64Url(hmac(signingInput));
        return signingInput + "." + signature;
    }

    public Map<String, String> parse(String token) {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            throw new IllegalArgumentException("Invalid token");
        }
        String signingInput = parts[0] + "." + parts[1];
        String expected = base64Url(hmac(signingInput));
        if (!constantTimeEquals(expected, parts[2])) {
            throw new IllegalArgumentException("Invalid signature");
        }
        String payloadJson = new String(Base64.getUrlDecoder().decode(parts[1]), StandardCharsets.UTF_8);
        String sub = extract(payloadJson, "sub");
        String role = extract(payloadJson, "role");
        String exp = extract(payloadJson, "exp");
        if (exp != null && Long.parseLong(exp) < Instant.now().getEpochSecond()) {
            throw new IllegalArgumentException("Token expired");
        }
        Map<String, String> map = new HashMap<>();
        map.put("username", sub);
        map.put("role", role);
        return map;
    }

    private byte[] hmac(String data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException("HMAC error", e);
        }
    }

    private static String base64Url(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static String base64Url(String value) {
        return base64Url(value.getBytes(StandardCharsets.UTF_8));
    }

    private static String extract(String json, String key) {
        String token = "\"" + key + "\":\"";
        int start = json.indexOf(token);
        if (start < 0) {
            return null;
        }
        start += token.length();
        int end = json.indexOf('"', start);
        return json.substring(start, end);
    }

    private static boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) {
            return false;
        }
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }
}