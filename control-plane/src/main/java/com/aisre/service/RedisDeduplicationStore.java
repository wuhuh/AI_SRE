package com.aisre.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Component
public class RedisDeduplicationStore implements DeduplicationStore {

    private static final Logger log = LoggerFactory.getLogger(RedisDeduplicationStore.class);

    private static final String KEY_PREFIX = "aisre:dedup:";

    private final StringRedisTemplate redisTemplate;

    public RedisDeduplicationStore(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public boolean putIfAbsent(String key, Duration ttl) {
        // P1-CP-15: redis 故障 fail-open——去重不可用时放行告警（宁可重复处理，
        // 不可让告警管道 500）
        try {
            Boolean success = redisTemplate.opsForValue().setIfAbsent(KEY_PREFIX + key, "1", ttl);
            return Boolean.TRUE.equals(success);
        } catch (Exception e) {
            log.warn("redis dedup unavailable, fail-open for key={}: {}", key, e.getMessage());
            return true;
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
