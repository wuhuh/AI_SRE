package com.aisre.api;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/**
 * P2-CP-21: 业务健康检查——并行探测 DB 与 Redis 依赖，30s 内返回聚合结果。
 * 组合健康：全部通过 → ok；任一依赖不可用 → degraded（HTTP 仍 200，探活用
 * actuator /health/liveness，管理端口 8085）。
 * ponytail: 两个依赖用 CompletableFuture 并行即可，不值得引反应式/批量探测框架。
 */
@RestController
public class HealthController {

    @Autowired
    private DataSource dataSource;

    @Autowired
    private StringRedisTemplate redisTemplate;

    @GetMapping({"/health", "/actuator/health"})
    public Map<String, Object> health() {
        CompletableFuture<Boolean> db = CompletableFuture.supplyAsync(this::checkDb);
        CompletableFuture<Boolean> redis = CompletableFuture.supplyAsync(this::checkRedis);
        boolean dbOk;
        boolean redisOk;
        try {
            dbOk = db.get(10, TimeUnit.SECONDS);
            redisOk = redis.get(10, TimeUnit.SECONDS);
        } catch (Exception e) {
            db.cancel(true);
            redis.cancel(true);
            return Map.of("status", "degraded", "db", false, "redis", false,
                    "error", String.valueOf(e.getMessage()));
        }
        String status = dbOk && redisOk ? "ok" : "degraded";
        return Map.of("status", status, "db", dbOk, "redis", redisOk);
    }

    private boolean checkDb() {
        try (Connection conn = dataSource.getConnection()) {
            return conn.isValid(5);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean checkRedis() {
        try {
            Boolean ok = redisTemplate.execute(
                    (org.springframework.data.redis.core.RedisCallback<Boolean>)
                            conn -> "PONG".equals(conn.ping()));
            return Boolean.TRUE.equals(ok);
        } catch (Exception e) {
            return false;
        }
    }
}
