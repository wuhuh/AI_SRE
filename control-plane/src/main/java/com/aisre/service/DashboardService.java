package com.aisre.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class DashboardService {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .build();

    private final List<Map<String, String>> services;

    public DashboardService(
            @Value("${aisre.services.gateway-url:http://gateway:8000}") String gatewayUrl,
            @Value("${aisre.services.order-url:http://order-service:8002}") String orderUrl,
            @Value("${aisre.services.inventory-url:http://inventory-service:8003}") String inventoryUrl,
            @Value("${aisre.services.payment-url:http://payment-service:8001}") String paymentUrl) {
        this.services = List.of(
                Map.of("name", "api-gateway", "url", gatewayUrl + "/health"),
                Map.of("name", "order-service", "url", orderUrl + "/health"),
                Map.of("name", "inventory-service", "url", inventoryUrl + "/health"),
                Map.of("name", "payment-service", "url", paymentUrl + "/health")
        );
    }

    public List<Map<String, Object>> health() {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, String> service : services) {
            String name = service.get("name");
            String url = service.get("url");
            long start = System.currentTimeMillis();
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .timeout(Duration.ofSeconds(3))
                        .GET()
                        .build();
                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
                long latency = System.currentTimeMillis() - start;
                boolean healthy = response.statusCode() >= 200 && response.statusCode() < 300;
                result.add(Map.of(
                        "service", name,
                        "status", healthy ? "UP" : "DOWN",
                        "latencyMs", latency,
                        "checkedAt", Instant.now().toString()
                ));
            } catch (Exception e) {
                long latency = System.currentTimeMillis() - start;
                result.add(Map.of(
                        "service", name,
                        "status", "DOWN",
                        "latencyMs", latency,
                        "error", e.getMessage(),
                        "checkedAt", Instant.now().toString()
                ));
            }
        }
        return result;
    }
}