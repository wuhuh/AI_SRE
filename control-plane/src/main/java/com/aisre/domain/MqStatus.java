package com.aisre.domain;

/** P3-CP-25: outbox 投递状态枚举化（PENDING 待发 → SENT 已发；失败随扫描器重试）。 */
public enum MqStatus {
    PENDING,
    SENT
}
