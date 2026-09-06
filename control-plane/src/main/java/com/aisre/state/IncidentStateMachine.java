package com.aisre.state;

import com.aisre.domain.IncidentStatus;

import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public final class IncidentStateMachine {

    private static final Map<IncidentStatus, Set<IncidentStatus>> TRANSITIONS = new EnumMap<>(IncidentStatus.class);

    static {
        TRANSITIONS.put(IncidentStatus.DETECTED, Set.of(IncidentStatus.TRIAGING, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.TRIAGING, Set.of(IncidentStatus.DIAGNOSING, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.DIAGNOSING, Set.of(IncidentStatus.ROOT_CAUSE_FOUND, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.ROOT_CAUSE_FOUND, Set.of(IncidentStatus.WAITING_APPROVAL, IncidentStatus.VERIFYING, IncidentStatus.FAILED));
        // P1-CP-12: REJECT 回 ROOT_CAUSE_FOUND（操作者重新诊断/换方案后可再建审批）
        TRANSITIONS.put(IncidentStatus.WAITING_APPROVAL, Set.of(IncidentStatus.REMEDIATING, IncidentStatus.VERIFYING, IncidentStatus.ROOT_CAUSE_FOUND, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.REMEDIATING, Set.of(IncidentStatus.VERIFYING, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.VERIFYING, Set.of(IncidentStatus.RESOLVED, IncidentStatus.DIAGNOSING, IncidentStatus.FAILED));
        TRANSITIONS.put(IncidentStatus.RESOLVED, Set.of());
        // FAILED is terminal; allow manual reset to TRIAGING in ops workflows
        TRANSITIONS.put(IncidentStatus.FAILED, Set.of(IncidentStatus.TRIAGING));
    }

    private IncidentStateMachine() {
    }

    public static boolean canTransition(IncidentStatus from, IncidentStatus to) {
        return TRANSITIONS.getOrDefault(from, new HashSet<>()).contains(to);
    }

    public static IncidentStatus transition(IncidentStatus from, IncidentStatus to) {
        if (!canTransition(from, to)) {
            throw new IllegalStateException("Invalid incident transition: " + from + " -> " + to);
        }
        return to;
    }
}