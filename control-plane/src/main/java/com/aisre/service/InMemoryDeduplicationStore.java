package com.aisre.service;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryDeduplicationStore implements DeduplicationStore {

    private record Entry(String token, Instant createdAt, Duration ttl) {
        boolean expired() {
            return createdAt.plus(ttl).isBefore(Instant.now());
        }
    }

    private final Map<String, Entry> store = new ConcurrentHashMap<>();

    @Override
    public String putIfAbsent(String key, Duration ttl) {
        String token = UUID.randomUUID().toString();
        Entry now = new Entry(token, Instant.now(), ttl);
        Entry existing = store.putIfAbsent(key, now);
        if (existing == null) {
            return token;
        }
        if (existing.expired()) {
            // 过期标记可被抢占；只有替换成功（仍是旧值）才算拿到所有权
            if (store.replace(key, existing, now)) {
                return token;
            }
        }
        return null;
    }

    @Override
    public boolean releaseIfOwner(String key, String token) {
        if (token == null) {
            return false;
        }
        boolean[] removed = {false};
        store.computeIfPresent(key, (k, e) -> {
            if (token.equals(e.token()) && !e.expired()) {
                removed[0] = true;
                return null; // 移除
            }
            return e; // 不是自己的标记，不动
        });
        return removed[0];
    }

    @Override
    public void delete(String key) {
        store.remove(key);
    }
}
