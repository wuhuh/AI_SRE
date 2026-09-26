package com.aisre.service;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InMemoryDeduplicationStoreTest {

    @Test
    void shouldReturnTokenForFirstInsertAndNullForDuplicate() {
        InMemoryDeduplicationStore store = new InMemoryDeduplicationStore();
        String token = store.putIfAbsent("payment:latency:payment-1", Duration.ofMinutes(5));
        assertNotNull(token);
        assertNull(store.putIfAbsent("payment:latency:payment-1", Duration.ofMinutes(5)));
    }

    @Test
    void shouldReturnTokenAfterDelete() {
        InMemoryDeduplicationStore store = new InMemoryDeduplicationStore();
        store.putIfAbsent("key", Duration.ofMinutes(5));
        store.delete("key");
        assertNotNull(store.putIfAbsent("key", Duration.ofMinutes(5)));
    }

    /**
     * 文档 5.5：落库失败后按自己的 token 释放；不能误删别人后来写入的标记。
     */
    @Test
    void releaseOnlyRemovesOwnToken() {
        InMemoryDeduplicationStore store = new InMemoryDeduplicationStore();
        String first = store.putIfAbsent("key", Duration.ofMinutes(5));
        assertNotNull(first);

        // 自己释放成功 → 之后可重新写入
        assertTrue(store.releaseIfOwner("key", first));
        String second = store.putIfAbsent("key", Duration.ofMinutes(5));
        assertNotNull(second);
        assertNotEquals(first, second);

        // 旧 token 再释放：不匹配 → 不删除（否则会误删 second 的标记）
        assertFalse(store.releaseIfOwner("key", first));
        // second 的标记仍在：再次写入仍判重复
        assertNull(store.putIfAbsent("key", Duration.ofMinutes(5)));

        // 未知 token 释放同样无效
        assertFalse(store.releaseIfOwner("key", "someone-else"));
    }
}
