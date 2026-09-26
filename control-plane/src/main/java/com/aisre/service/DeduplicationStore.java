package com.aisre.service;

import java.time.Duration;

public interface DeduplicationStore {

    /**
     * 文档 5.5：条件写入并返回本次占用的 owner token。
     * 返回 null = 标记已存在（重复告警）。
     * token 用于失败时按归属清理——不能无条件 delete，否则会误删
     * 其他实例在窗口内新写入的标记。
     */
    String putIfAbsent(String key, Duration ttl);

    /**
     * 仅当当前标记确由本 token 写入时才删除（比较后删除）。
     * 用于「Redis 标记成功但数据库落库失败」的回滚——文档 5.5 的
     * 跨系统窗口：否则上游重试同一条告警会被残留标记压住，告警就此丢失。
     */
    boolean releaseIfOwner(String key, String token);

    void delete(String key);
}
