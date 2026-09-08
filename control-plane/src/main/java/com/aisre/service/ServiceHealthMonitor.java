package com.aisre.service;

import com.aisre.api.dto.AlertRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;

// health.monitor.enabled=false 可关（CI/IT 中无 compose demo 服务，
// 探活失败会发告警污染测试的 incident 计数断言）
@Service
@org.springframework.boot.autoconfigure.condition.ConditionalOnProperty(
        name = "health.monitor.enabled", havingValue = "true", matchIfMissing = true)
public class ServiceHealthMonitor {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .build();

    private final List<Map<String, String>> services;
    private final AlertService alertService;

    public ServiceHealthMonitor(AlertService alertService) {
        this.alertService = alertService;
        this.services = List.of(
                Map.of("name", "api-gateway", "url", System.getenv().getOrDefault("AISRE_GATEWAY_URL", "http://gateway:8000") + "/health"),
                Map.of("name", "order-service", "url", System.getenv().getOrDefault("AISRE_ORDER_URL", "http://order-service:8002") + "/health"),
                Map.of("name", "inventory-service", "url", System.getenv().getOrDefault("AISRE_INVENTORY_URL", "http://inventory-service:8003") + "/health"),
                Map.of("name", "payment-service", "url", System.getenv().getOrDefault("AISRE_PAYMENT_URL", "http://payment-service:8001") + "/health")
        );
    }

    @Scheduled(fixedDelay = 15000)
    public void checkHealth() {
        for (Map<String, String> service : services) {
            String name = service.get("name");
            String url = service.get("url");
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .timeout(Duration.ofSeconds(3))
                        .GET()
                        .build();
                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() < 200 || response.statusCode() >= 300) {
                    alertService.ingest(new AlertRequest(
                            name,
                            "service_unhealthy",
                            "health-check",
                            "P1",
                            name + " health check failed with status " + response.statusCode(),
                            Map.of("check", "health"),
                            Instant.now()
                    ));
                }
            } catch (Exception e) {
                alertService.ingest(new AlertRequest(
                        name,
                        "service_down",
                        "health-check",
                        "P1",
                        name + " is not reachable: " + e.getMessage(),
                        Map.of("check", "health"),
                        Instant.now()
                ));
            }
        }
    }
}