package com.aisre.api;

import com.aisre.api.dto.LoginRequest;
import com.aisre.security.AuthService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;

/**
 * P0-06: 登录安全加固。
 * - 口令支持 BCrypt 哈希（以 "$2" 开头）或明文兼容（迁移期）；
 * - strict 模式下拒绝默认口令启动；
 * - 按用户名限速：10 分钟内失败 ≥5 次锁定。
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private static final int MAX_FAILURES = 5;
    private static final long FAILURE_WINDOW_MS = 10 * 60 * 1000L;
    private static final String DEFAULT_ADMIN_PASSWORD = "admin";
    private static final String DEFAULT_OPERATOR_PASSWORD = "operator";
    private static final String DEFAULT_VIEWER_PASSWORD = "viewer";

    private final AuthService authService;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private final Map<String, Deque<Long>> failures = new HashMap<>();

    private final String adminUser;
    private final String adminPassword;
    private final String operatorUser;
    private final String operatorPassword;
    private final String viewerUser;
    private final String viewerPassword;

    public AuthController(AuthService authService,
                          @Value("${aisre.security.strict:false}") boolean strict,
                          @Value("${aisre.admin.user:admin}") String adminUser,
                          @Value("${aisre.admin.password:admin}") String adminPassword,
                          @Value("${aisre.operator.user:operator}") String operatorUser,
                          @Value("${aisre.operator.password:operator}") String operatorPassword,
                          @Value("${aisre.viewer.user:viewer}") String viewerUser,
                          @Value("${aisre.viewer.password:viewer}") String viewerPassword) {
        this.authService = authService;
        this.adminUser = adminUser;
        this.adminPassword = adminPassword;
        this.operatorUser = operatorUser;
        this.operatorPassword = operatorPassword;
        this.viewerUser = viewerUser;
        this.viewerPassword = viewerPassword;
        if (strict && (isDefaultPassword(adminPassword, DEFAULT_ADMIN_PASSWORD)
                || isDefaultPassword(operatorPassword, DEFAULT_OPERATOR_PASSWORD)
                || isDefaultPassword(viewerPassword, DEFAULT_VIEWER_PASSWORD))) {
            throw new IllegalStateException(
                    "Refusing to start: default passwords are not allowed with AISRE_SECURITY_STRICT=true. "
                            + "Set AISRE_ADMIN_PASSWORD / AISRE_OPERATOR_PASSWORD / AISRE_VIEWER_PASSWORD "
                            + "(plaintext or BCrypt hash starting with $2).");
        }
    }

    private static boolean isDefaultPassword(String configured, String defaultValue) {
        return configured == null || configured.isBlank() || defaultValue.equals(configured);
    }

    boolean passwordMatches(String stored, String raw) {
        if (stored != null && stored.startsWith("$2")) {
            return encoder.matches(raw, stored);
        }
        return stored != null && stored.equals(raw);
    }

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody LoginRequest request) {
        throttleCheck(request.username());
        String role = null;
        if (adminUser.equals(request.username()) && passwordMatches(adminPassword, request.password())) {
            role = "ADMIN";
        } else if (operatorUser.equals(request.username()) && passwordMatches(operatorPassword, request.password())) {
            role = "OPERATOR";
        } else if (viewerUser.equals(request.username()) && passwordMatches(viewerPassword, request.password())) {
            role = "VIEWER";
        }
        if (role == null) {
            failures.computeIfAbsent(request.username(), k -> new ArrayDeque<>()).addLast(System.currentTimeMillis());
            throw new IllegalArgumentException("Invalid username or password");
        }
        failures.remove(request.username());
        return Map.of(
                "token", authService.issueToken(request.username(), role),
                "tokenType", "Bearer",
                "role", role
        );
    }

    private void throttleCheck(String username) {
        Deque<Long> attempts = failures.get(username);
        if (attempts == null) {
            return;
        }
        long now = System.currentTimeMillis();
        attempts.removeIf(t -> now - t > FAILURE_WINDOW_MS);
        if (attempts.size() >= MAX_FAILURES) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS,
                    "Too many failed logins; try again later");
        }
    }
}
