package com.aisre.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String DEFAULT_SECRET = "dev-secret-change-me";

    private final byte[] secret;

    /**
     * P0-06: strict 模式下拒绝默认/过短密钥启动（compose 与 K8s 开启 AISRE_SECURITY_STRICT=true）。
     * 双构造器时 Spring 需要显式指定注入入口。
     */
    @org.springframework.beans.factory.annotation.Autowired
    public AuthService(@Value("${aisre.jwt.secret:dev-secret-change-me}") String secret,
                       @Value("${aisre.security.strict:false}") boolean strict) {
        if (strict && (secret == null || secret.isBlank() || DEFAULT_SECRET.equals(secret)
                || secret.getBytes(StandardCharsets.UTF_8).length < 32)) {
            throw new IllegalStateException(
                    "Refusing to start: aisre.jwt.secret is missing/default/too short (<32 bytes). "
                            + "Set AISRE_JWT_SECRET (>=32 bytes) before enabling AISRE_SECURITY_STRICT.");
        }
        this.secret = secret.getBytes(StandardCharsets.UTF_8);
    }

    /** 测试与本地便捷构造（非 strict）。 */
    public AuthService(String secret) {
        this(secret, false);
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
        JsonNode payload;
        try {
            payload = MAPPER.readTree(payloadJson);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid payload", e);
        }
        // P0-06: exp 为数字，旧 extract() 只找带引号的字符串值，导致过期校验从不生效
        long exp = payload.path("exp").asLong(0L);
        if (exp <= 0 || exp < Instant.now().getEpochSecond()) {
            throw new IllegalArgumentException("Token expired");
        }
        Map<String, String> map = new HashMap<>();
        map.put("username", payload.path("sub").asText(null));
        map.put("role", payload.path("role").asText(null));
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