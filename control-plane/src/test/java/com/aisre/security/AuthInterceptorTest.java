package com.aisre.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * P0-05: Agent 回调必须携带 X-Agent-Token；用户 JWT 逻辑不受影响。
 */
class AuthInterceptorTest {

    private AuthInterceptor interceptor(String agentToken) {
        return new AuthInterceptor(new StubAuthService(), agentToken);
    }

    private MockHttpServletRequest request(String method, String uri) {
        MockHttpServletRequest req = new MockHttpServletRequest(method, uri);
        req.setRequestURI(uri);
        return req;
    }

    @Test
    void agentCallbackWithoutTokenIsRejected() throws Exception {
        MockHttpServletResponse resp = new MockHttpServletResponse();
        boolean ok = interceptor("secret-token").preHandle(
                request("POST", "/api/v1/incidents/1/diagnosis"), resp, new Object());
        assertFalse(ok);
        assertEquals(401, resp.getStatus());
    }

    @Test
    void agentCallbackWithCorrectTokenPasses() throws Exception {
        MockHttpServletRequest req = request("POST", "/api/v1/incidents/1/diagnosis");
        req.addHeader("X-Agent-Token", "secret-token");
        MockHttpServletResponse resp = new MockHttpServletResponse();
        assertTrue(interceptor("secret-token").preHandle(req, resp, new Object()));
    }

    @Test
    void agentCallbackWithWrongTokenIsRejected() throws Exception {
        MockHttpServletRequest req = request("POST", "/api/v1/tasks/7/claim");
        req.addHeader("X-Agent-Token", "wrong");
        MockHttpServletResponse resp = new MockHttpServletResponse();
        assertFalse(interceptor("secret-token").preHandle(req, resp, new Object()));
        assertEquals(401, resp.getStatus());
    }

    @Test
    void unconfiguredAgentTokenFailsClosed() throws Exception {
        MockHttpServletRequest req = request("POST", "/api/v1/tasks/7/complete");
        req.addHeader("X-Agent-Token", "anything");
        MockHttpServletResponse resp = new MockHttpServletResponse();
        assertFalse(interceptor("  ").preHandle(req, resp, new Object()));
        assertEquals(503, resp.getStatus());
    }

    @Test
    void taskEndpointsRequireAgentTokenButOtherWritesDoNot() throws Exception {
        MockHttpServletResponse resp = new MockHttpServletResponse();
        // 任务端点属于 agent 回调面
        assertFalse(interceptor("secret-token").preHandle(
                request("POST", "/api/v1/tasks/7/fail"), resp, new Object()));
        // 其它非保护写端点保持开放（与原行为一致）
        assertTrue(interceptor("secret-token").preHandle(
                request("POST", "/api/v1/anything-else"), new MockHttpServletResponse(), new Object()));
    }

    private static class StubAuthService extends AuthService {
        StubAuthService() {
            super("0123456789abcdef0123456789abcdef", false);
        }

        @Override
        public Map<String, String> parse(String token) {
            return Map.of("role", "ADMIN");
        }
    }
}
