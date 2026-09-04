package com.aisre.service;

public class NoopAgentJobProducer implements AgentJobProducer {

    @Override
    public void sendDiagnosisTask(Long incidentId) {
        // Intentionally empty for local/unit tests.
    }
}