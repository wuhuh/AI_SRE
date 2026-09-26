package com.aisre.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

@Component
public class RedisDeduplicationStore implements DeduplicationStore {

    private static final Logger log = LoggerFactory.getLogger(RedisDeduplicationStore.class);

    private static final String KEY_PREFIX = "aisre:dedup:";

    // 文档 5.3/5.5：SET key token NX EX 原子完成条件写入与过期；
    // 释放时用 Lua 比较后删除——「先 GET 再 DEL」两步之间标记可能已易主。
    private static final DefaultRedisScript<Long> RELEASE_IF_OWNER = new DefaultRedisScript<>(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
                    + "return redis.call('del', KEYS[1]) "
                    + "else return 0 end", Long.class);

    private final StringRedisTemplate redisTemplate;

    public RedisDeduplicationStore(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public String putIfAbsent(String key, Duration ttl) {
        // P1-CP-15: redis 故障 fail-open——去重不可用时放行告警（宁可重复处理，
        // 不可让告警管道 500）。fail-open 作用于「可用性」，与执行凭据的
        // fail-closed 是两个保护对象，不能一概而论。
        try {
            String token = UUID.randomUUID().toString();
            Boolean success = redisTemplate.opsForValue().setIfAbsent(KEY_PREFIX + key, token, ttl);
            return Boolean.TRUE.equals(success) ? token : null;
        } catch (Exception e) {
            log.warn("redis dedup unavailable, fail-open for key={}: {}", key, e.getMessage());
            return "fail-open:" + UUID.randomUUID();
        }
    }

    @Override
    public boolean releaseIfOwner(String key, String token) {
        if (token == null || token.startsWith("fail-open:")) {
            // fail-open 放行的告警没有真实标记，无需也无从释放
            return false;
        }
        try {
            Long released = redisTemplate.execute(RELEASE_IF_OWNER,
                    List.of(KEY_PREFIX + key), token);
            return released != null && released > 0;
        } catch (Exception e) {
            log.warn("redis dedup release failed for key={}: {} (标记将在 TTL 到期后自然消失)",
                    key, e.getMessage());
            return false;
        }
    }

    @Override
    public void delete(String key) {
        try {
            redisTemplate.delete(KEY_PREFIX + key);
        } catch (Exception e) {
            log.warn("redis dedup delete failed for key={}: {}", key, e.getMessage());
        }
    }
}
