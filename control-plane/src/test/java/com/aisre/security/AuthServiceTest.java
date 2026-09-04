package com.aisre.security;

import org.junit.jupiter.api.Test;

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
}