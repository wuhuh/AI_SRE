package com.aisre.domain;

import java.util.Set;

/**
 * 文档 8.6：闭集根因标签——与 agent-runtime 的 RCA_CANDIDATE_LABELS 保持同一集合。
 * 闭集不能只靠提示词约束：控制面落库前也校验，模型编造的非法标签
 * 不能因为「不是 unknown 字符串」就被视为已找到根因。
 */
public final class RcaLabels {

    public static final Set<String> LABELS = Set.of(
            "cpu_saturation",
            "database_connection_pool_exhausted",
            "downstream_http_timeout",
            "memory_leak",
            "pod_crashloopbackoff",
            "redis_connection_pool_exhausted",
            "redis_slow_command",
            "rocketmq_message_backlog",
            "slow_sql",
            "thread_pool_exhausted"
    );

    private RcaLabels() {
    }

    /** 归一化：小写、空格/连字符转下划线（与 Python normalize_label 对齐）。 */
    public static String normalize(String raw) {
        if (raw == null) {
            return "";
        }
        return raw.trim().toLowerCase().replace('-', '_').replace(' ', '_');
    }

    /**
     * @return 合法标签归一化后原样返回；"unknown" 返回 "unknown"；
     *         非法值返回 "unknown"（由调用方决定是否审计记录原始值）。
     */
    public static String normalizeOrUnknown(String raw) {
        String normalized = normalize(raw);
        if (normalized.isEmpty() || "unknown".equals(normalized)) {
            return "unknown";
        }
        return LABELS.contains(normalized) ? normalized : "unknown";
    }
}
