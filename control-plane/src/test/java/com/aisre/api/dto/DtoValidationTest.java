package com.aisre.api.dto;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * P1-CP-18: 写路径 DTO 校验注解生效（records 的组件注解会传播到字段）。
 */
class DtoValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        factory.close();
    }

    @Test
    void alertRequestRequiresServiceAndAlertName() {
        var violations = validator.validate(new AlertRequest("", " ", null, null, null, null, null));
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("service")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("alertName")));

        var ok = validator.validate(new AlertRequest("payment-service", "HighLatency", "p-1", "P1", "s", null, null));
        assertTrue(ok.isEmpty());
    }

    @Test
    void loginRequestRequiresCredentials() {
        assertFalse(validator.validate(new LoginRequest("", "x")).isEmpty());
        assertTrue(validator.validate(new LoginRequest("admin", "x")).isEmpty());
    }

    @Test
    void diagnosisRequestRequiresRootCause() {
        assertFalse(validator.validate(new DiagnosisRequest(null, 0.5, null, null, null, null)).isEmpty());
        assertTrue(validator.validate(new DiagnosisRequest("slow_sql", 0.5, null, null, null, 7L)).isEmpty());
    }

    @Test
    void verificationRequestRequiresStatus() {
        assertFalse(validator.validate(new VerificationRequest("  ", null, null)).isEmpty());
        assertTrue(validator.validate(new VerificationRequest("RECOVERED", null, null)).isEmpty());
    }
}
