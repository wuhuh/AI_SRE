package com.aisre.integration;

import org.junit.jupiter.api.Test;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.junit.jupiter.api.Assertions.assertTrue;

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
}