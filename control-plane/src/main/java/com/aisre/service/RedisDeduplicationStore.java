package com.aisre.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Component
public class RedisDeduplicationStore implements DeduplicationStore {

    private static final String KEY_PREFIX = "aisre:dedup:";

    private final StringRedisTemplate redisTemplate;

    public RedisDeduplicationStore(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public boolean putIfAbsent(String key, Duration ttl) {
        Boolean success = redisTemplate.opsForValue().setIfAbsent(KEY_PREFIX + key, "1", ttl);
        return Boolean.TRUE.equals(success);
    }

    @Override
    public void delete(String key) {
        redisTemplate.delete(KEY_PREFIX + key);
    }
}