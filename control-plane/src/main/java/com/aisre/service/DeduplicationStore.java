package com.aisre.service;

import java.time.Duration;

public interface DeduplicationStore {

    boolean putIfAbsent(String key, Duration ttl);

    void delete(String key);
}