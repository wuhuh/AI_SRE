package com.aisre.service;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InMemoryDeduplicationStoreTest {

    @Test
    void shouldReturnTrueForFirstInsertAndFalseForDuplicate() {
        InMemoryDeduplicationStore store = new InMemoryDeduplicationStore();
        assertTrue(store.putIfAbsent("payment:latency:payment-1", Duration.ofMinutes(5)));
        assertFalse(store.putIfAbsent("payment:latency:payment-1", Duration.ofMinutes(5)));
    }

    @Test
    void shouldReturnTrueAfterDelete() {
        InMemoryDeduplicationStore store = new InMemoryDeduplicationStore();
        store.putIfAbsent("key", Duration.ofMinutes(5));
        store.delete("key");
        assertTrue(store.putIfAbsent("key", Duration.ofMinutes(5)));
    }
}