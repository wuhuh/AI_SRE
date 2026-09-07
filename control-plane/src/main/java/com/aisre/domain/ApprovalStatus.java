package com.aisre.domain;

/** P3-CP-25: 审批状态枚举化（PENDING 唯一可决定；终态不可逆）。 */
public enum ApprovalStatus {
    PENDING,
    APPROVED,
    REJECTED
}
