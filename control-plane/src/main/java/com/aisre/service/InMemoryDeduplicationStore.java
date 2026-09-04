package com.aisre.service;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryDeduplicationStore implements DeduplicationStore {

    private record Entry(Instant createdAt, Duration ttl) {
        boolean expired() {
            return createdAt.plus(ttl).isBefore(Instant.now());
        }
    }

    private final Map<String, Entry> store = new ConcurrentHashMap<>();

    @Override
    public boolean putIfAbsent(String key, Duration ttl) {
        Entry now = new Entry(Instant.now(), ttl);
        Entry existing = store.putIfAbsent(key, now);
        if (existing == null) {
            return true;
        }
        if (existing.expired()) {
            store.replace(key, existing, now);
            return true;
        }
        return false;
    }

    @Override
    public void delete(String key) {
        store.remove(key);
    }
}