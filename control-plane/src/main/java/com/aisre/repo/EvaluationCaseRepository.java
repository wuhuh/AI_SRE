package com.aisre.repo;

import com.aisre.domain.EvaluationCase;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EvaluationCaseRepository extends JpaRepository<EvaluationCase, Long> {
}