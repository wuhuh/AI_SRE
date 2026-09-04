package com.aisre.api;

import com.aisre.api.dto.LoginRequest;
import com.aisre.security.AuthService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final String adminUser;
    private final String adminPassword;
    private final String operatorUser;
    private final String operatorPassword;
    private final String viewerUser;
    private final String viewerPassword;

    public AuthController(AuthService authService,
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
    }

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody LoginRequest request) {
        String role = null;
        if (adminUser.equals(request.username()) && adminPassword.equals(request.password())) {
            role = "ADMIN";
        } else if (operatorUser.equals(request.username()) && operatorPassword.equals(request.password())) {
            role = "OPERATOR";
        } else if (viewerUser.equals(request.username()) && viewerPassword.equals(request.password())) {
            role = "VIEWER";
        }
        if (role == null) {
            throw new IllegalArgumentException("Invalid username or password");
        }
        return Map.of(
                "token", authService.issueToken(request.username(), role),
                "tokenType", "Bearer",
                "role", role
        );
    }
}