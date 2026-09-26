package com.aisre.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * 文档 8.6：闭集根因标签代码级校验。集合与 agent-runtime 的
 * RCA_CANDIDATE_LABELS 一致；非法标签归一为 unknown，不再「因为不是
 * unknown 字符串就被视为已找到根因」。
 */
class RcaLabelsTest {

    @Test
    void acceptsAllTenContractLabels() {
        assertEquals("cpu_saturation", RcaLabels.normalizeOrUnknown("cpu_saturation"));
        assertEquals("redis_connection_pool_exhausted",
                RcaLabels.normalizeOrUnknown("Redis-Connection-Pool-Exhausted"));
        assertEquals("slow_sql", RcaLabels.normalizeOrUnknown("Slow SQL"));
    }

    @Test
    void normalizesCaseAndSeparators() {
        assertEquals("memory_leak", RcaLabels.normalizeOrUnknown("  MEMORY_LEAK "));
    }

    @Test
    void unknownPassesThroughAsUnknown() {
        assertEquals("unknown", RcaLabels.normalizeOrUnknown("unknown"));
        assertEquals("unknown", RcaLabels.normalizeOrUnknown("UNKNOWN"));
        assertEquals("unknown", RcaLabels.normalizeOrUnknown(null));
        assertEquals("unknown", RcaLabels.normalizeOrUnknown("   "));
    }

    @Test
    void hallucinatedLabelsAreRejected() {
        // 模型编造的标签 → unknown（不能冒充已找到根因）
        assertEquals("unknown", RcaLabels.normalizeOrUnknown("banana_peel"));
        assertEquals("unknown", RcaLabels.normalizeOrUnknown("alien_invasion"));
    }
}
