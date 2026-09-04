package com.aisre.repo;

import com.aisre.domain.Runbook;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RunbookRepository extends JpaRepository<Runbook, Long> {

    List<Runbook> findByServiceContainingIgnoreCase(String service);
}