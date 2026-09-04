package com.aisre.api;

import com.aisre.api.dto.LoginRequest;
import com.aisre.security.AuthService;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthControllerTest {

    private AuthController controller() {
        return new AuthController(new AuthService("test-secret"), false,
                "admin", "admin", "operator", "operator", "viewer", "viewer");
    }

    private LoginRequest login(String user, String password) {
        return new LoginRequest(user, password);
    }

    @Test
    void shouldLoginWithLegacyPlaintextPassword() {
        Map<String, String> result = controller().login(login("admin", "admin"));
        assertEquals("ADMIN", result.get("role"));
    }

    @Test
    void shouldLoginWithBcryptStoredPassword() {
        String hash = new BCryptPasswordEncoder().encode("s3cret!");
        AuthController controller = new AuthController(new AuthService("test-secret"), false,
                "admin", hash, "operator", "operator", "viewer", "viewer");
        assertEquals("ADMIN", controller.login(login("admin", "s3cret!")).get("role"));
        assertThrows(IllegalArgumentException.class, () -> controller.login(login("admin", "admin")));
    }

    @Test
    void shouldRejectWrongPassword() {
        assertThrows(IllegalArgumentException.class, () -> controller().login(login("admin", "wrong")));
    }

    @Test
    void shouldLockoutAfterFiveFailures() {
        AuthController controller = controller();
        for (int i = 0; i < 5; i++) {
            assertThrows(IllegalArgumentException.class, () -> controller.login(login("admin", "bad")));
        }
        // 第 6 次尝试（即使口令正确）在锁定窗口内被拒绝
        assertThrows(ResponseStatusException.class, () -> controller.login(login("admin", "admin")));
    }

    @Test
    void bcryptMatchesOnlyForSameRawPassword() {
        AuthController controller = controller();
        String hash = new BCryptPasswordEncoder().encode("abc");
        assertTrue(controller.passwordMatches(hash, "abc"));
        assertFalse(controller.passwordMatches(hash, "abd"));
    }

    @Test
    void strictModeRefusesDefaultPasswords() {
        assertThrows(IllegalStateException.class,
                () -> new AuthController(new AuthService("test-secret"), true,
                        "admin", "admin", "operator", "operator", "viewer", "viewer"));
    }
}
