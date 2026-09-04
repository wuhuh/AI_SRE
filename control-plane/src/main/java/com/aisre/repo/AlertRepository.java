package com.aisre.repo;

import com.aisre.domain.Alert;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface AlertRepository extends JpaRepository<Alert, Long> {

    Optional<Alert> findFirstByFingerprintOrderByReceivedAtDesc(String fingerprint);

    List<Alert> findByIncidentId(Long incidentId);

    List<Alert> findByReceivedAtBetween(Instant start, Instant end);
}