package com.aisre.state;

import com.aisre.domain.IncidentStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class IncidentStateMachineTest {

    @Test
    void shouldAllowHappyPathTransitions() {
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.DETECTED, IncidentStatus.TRIAGING));
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.TRIAGING, IncidentStatus.DIAGNOSING));
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.DIAGNOSING, IncidentStatus.ROOT_CAUSE_FOUND));
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.WAITING_APPROVAL, IncidentStatus.REMEDIATING));
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.REMEDIATING, IncidentStatus.VERIFYING));
        assertTrue(IncidentStateMachine.canTransition(IncidentStatus.VERIFYING, IncidentStatus.RESOLVED));
    }

    @Test
    void shouldRejectInvalidTransitions() {
        assertFalse(IncidentStateMachine.canTransition(IncidentStatus.DETECTED, IncidentStatus.RESOLVED));
        assertFalse(IncidentStateMachine.canTransition(IncidentStatus.RESOLVED, IncidentStatus.DETECTED));
    }

    @Test
    void shouldThrowOnInvalidTransition() {
        assertThrows(IllegalStateException.class,
                () -> IncidentStateMachine.transition(IncidentStatus.DETECTED, IncidentStatus.RESOLVED));
    }
}