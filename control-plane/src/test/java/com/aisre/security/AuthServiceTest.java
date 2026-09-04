package com.aisre.security;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AuthServiceTest {

    @Test
    void shouldIssueAndParseToken() {
        AuthService authService = new AuthService("test-secret");
        String token = authService.issueToken("admin", "admin");
        Map<String, String> claims = authService.parse(token);
        assertEquals("admin", claims.get("username"));
        assertEquals("admin", claims.get("role"));
    }

    @Test
    void shouldParseOperatorRole() {
        AuthService authService = new AuthService("test-secret");
        String token = authService.issueToken("operator", "OPERATOR");
        assertEquals("OPERATOR", authService.parse(token).get("role"));
    }

    @Test
    void shouldRejectInvalidToken() {
        AuthService authService = new AuthService("test-secret");
        assertThrows(IllegalArgumentException.class, () -> authService.parse("a.b.c"));
    }

    @Test
    void shouldRejectExpiredToken() {
        // P0-06: exp 为数字，旧实现按带引号字符串解析导致过期校验从不生效
        AuthService authService = new AuthService("test-secret");
        String token = authService.issueToken("admin", "admin");
        String[] parts = token.split("\\.");
        String expiredPayload = Base64.getUrlEncoder().withoutPadding().encodeToString(
                "{\"sub\":\"admin\",\"role\":\"admin\",\"exp\":1000}".getBytes(StandardCharsets.UTF_8));
        String expiredToken = parts[0] + "." + expiredPayload + "." + parts[2];
        assertThrows(IllegalArgumentException.class, () -> authService.parse(expiredToken));
    }

    @Test
    void shouldRefuseDefaultOrShortSecretInStrictMode() {
        assertThrows(IllegalStateException.class, () -> new AuthService("dev-secret-change-me", true));
        assertThrows(IllegalStateException.class, () -> new AuthService("too-short", true));
        // 非 strict 下默认密钥仍可用于本地开发/测试
        new AuthService("dev-secret-change-me");
    }
}