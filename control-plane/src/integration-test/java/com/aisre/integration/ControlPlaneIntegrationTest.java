package com.aisre.integration;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.output.MigrateResult;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * P2-T-04: 迁移 + schema 冒烟 —— 原本只验容器启动（空转）。现在编程式执行
 * Flyway V1..V8 并断言关键表/列存在，独立于 Spring 上下文验证迁移自身可用。
 */
@Testcontainers
class ControlPlaneIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("aisre")
            .withUsername("aisre")
            .withPassword("aisre");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
            .withExposedPorts(6379);

    @Test
    void postgresAndRedisShouldStart() {
        assertTrue(postgres.isRunning());
        assertTrue(redis.isRunning());
        assertTrue(postgres.getJdbcUrl().contains("aisre"));
    }

    @Test
    void flywayMigrationsApplyAndSchemaHasExpectedShapes() throws Exception {
        MigrateResult result = Flyway.configure()
                .dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                .locations("classpath:db/migration")
                .load()
                .migrate();
        // V1..V9 全部落库（V8 = 删未用表，V9 = 证据溯源列）；
        // 新增迁移时同步此数（ponytail: 保持显式，漏更新即测试红——这正是目的）
        assertEquals(9, result.migrationsExecuted);

        try (Connection conn = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
             Statement st = conn.createStatement()) {
            // 关键列冒烟：任务租约/毒任务（P1-MQ-02/03）+ 证据溯源（P2-AR-09）
            assertColumn(st, "agent_task", "attempts");
            assertColumn(st, "agent_task", "mq_status");
            assertColumn(st, "evidence", "query");
            assertColumn(st, "evidence", "time_range");
            // V8 后未用表应不存在
            try (ResultSet rs = st.executeQuery(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('runbook','evaluation_case')")) {
                rs.next();
                assertEquals(0, rs.getInt(1), "V8 应已删除 runbook/evaluation_case");
            }
        }
    }

    private static void assertColumn(Statement st, String table, String column) throws Exception {
        try (ResultSet rs = st.executeQuery(
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='" + table
                        + "' AND column_name='" + column + "'")) {
            rs.next();
            assertEquals(1, rs.getInt(1), table + "." + column + " 应存在");
        }
    }
}
