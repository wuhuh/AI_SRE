package com.aisre.api;

import com.aisre.api.dto.AlertRequest;
import com.aisre.api.dto.AlertmanagerWebhook;
import com.aisre.service.AlertService;
import com.aisre.service.AlertmanagerAdapter;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/alerts")
public class AlertController {

    private final AlertService alertService;
    private final AlertmanagerAdapter alertmanagerAdapter;

    public AlertController(AlertService alertService, AlertmanagerAdapter alertmanagerAdapter) {
        this.alertService = alertService;
        this.alertmanagerAdapter = alertmanagerAdapter;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public AlertService.AlertResult ingest(@Valid @RequestBody AlertRequest request) {
        return alertService.ingest(request);
    }

    /** P0-07: Alertmanager webhook v4 契约端点。 */
    @PostMapping("/alertmanager")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public AlertmanagerAdapter.AdapterResult ingestAlertmanager(@RequestBody AlertmanagerWebhook webhook) {
        return alertmanagerAdapter.ingest(webhook);
    }
}
