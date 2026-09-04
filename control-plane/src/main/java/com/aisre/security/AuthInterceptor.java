package com.aisre.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    private final AuthService authService;

    public AuthInterceptor(AuthService authService) {
        this.authService = authService;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();
        String method = request.getMethod();

        // Read-only and internal agent callback endpoints are open for simplicity.
        if ("GET".equals(method)
                || path.equals("/api/v1/alerts")
                || path.equals("/api/v1/auth/login")
                || path.matches(".*/incidents/\\d+/(diagnosis|verification|remediations)")) {
            return true;
        }

        // User-facing write operations require ADMIN or OPERATOR.
        boolean protectedWrite = path.startsWith("/api/v1/approvals")
                || path.matches(".*/incidents/\\d+/transition");
        if (!protectedWrite) {
            return true;
        }

        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\":\"missing or invalid token\"}");
            return false;
        }
        try {
            java.util.Map<String, String> claims = authService.parse(auth.substring(7));
            String role = claims.get("role");
            if (!"ADMIN".equals(role) && !"OPERATOR".equals(role)) {
                response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                response.setContentType("application/json");
                response.getWriter().write("{\"error\":\"forbidden: insufficient role\"}");
                return false;
            }
            return true;
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"error\":\"invalid token\"}");
            return false;
        }
    }
}