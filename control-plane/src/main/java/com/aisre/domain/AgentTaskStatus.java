package com.aisre.domain;

/**
 * P3-CP-25: 任务状态枚举化（原裸字符串，QUEUED/RUNNING/终态流转与
 * 租约回收/毒任务判定全部依赖拼写，拼错即静默失联）。
 */
public enum AgentTaskStatus {
    QUEUED,
    RUNNING,
    COMPLETED,
    FAILED,
    DEAD
}
