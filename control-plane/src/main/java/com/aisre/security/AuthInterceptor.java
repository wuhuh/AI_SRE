package com.aisre.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * 认证拦截器：
 * - 用户写操作（审批/状态推进）：JWT（ADMIN/OPERATOR）；
 * - Agent 回调（诊断/验证/修复结果上报、任务领取/完成/失败）：静态 X-Agent-Token。
 * Agent token 为空 = fail-closed（回调一律拒绝），部署必须显式配置。
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

    private final AuthService authService;
    private final String agentToken;

    public AuthInterceptor(AuthService authService,
                           @Value("${aisre.agent.token:}") String agentToken) {
        this.authService = authService;
        this.agentToken = agentToken == null ? "" : agentToken.trim();
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();
        String method = request.getMethod();

        // Read-only endpoints stay open (query-path hardening is tracked separately).
        if ("GET".equals(method) || path.equals("/api/v1/auth/login")) {
            return true;
        }

        // Agent callbacks authenticate with the shared static token, not a user JWT.
        boolean agentCallback = path.matches(".*/incidents/\\d+/(diagnosis|verification|remediations)")
                || path.startsWith("/api/v1/tasks/");
        if (agentCallback) {
            return requireAgentToken(request, response);
        }

        // User-facing write operations require ADMIN or OPERATOR.
        boolean protectedWrite = path.startsWith("/api/v1/approvals")
                || path.matches(".*/incidents/\\d+/transition");
        if (!protectedWrite) {
            return true;
        }

        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "missing or invalid token");
        }
        try {
            java.util.Map<String, String> claims = authService.parse(auth.substring(7));
            String role = claims.get("role");
            if (!"ADMIN".equals(role) && !"OPERATOR".equals(role)) {
                return reject(response, HttpServletResponse.SC_FORBIDDEN, "forbidden: insufficient role");
            }
            return true;
        } catch (Exception e) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "invalid token");
        }
    }

    private boolean requireAgentToken(HttpServletRequest request, HttpServletResponse response) throws Exception {
        if (agentToken.isEmpty()) {
            return reject(response, HttpServletResponse.SC_SERVICE_UNAVAILABLE, "agent token not configured");
        }
        String provided = request.getHeader("X-Agent-Token");
        if (provided == null || !constantTimeEquals(provided.trim(), agentToken)) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "invalid agent token");
        }
        return true;
    }

    private static boolean constantTimeEquals(String a, String b) {
        return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    private static boolean reject(HttpServletResponse response, int status, String message) throws Exception {
        response.setStatus(status);
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"" + message + "\"}");
        return false;
    }
}
