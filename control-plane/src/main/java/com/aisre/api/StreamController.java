package com.aisre.api;

import com.aisre.service.IncidentEventService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/v1/stream")
public class StreamController {

    private final IncidentEventService eventService;

    public StreamController(IncidentEventService eventService) {
        this.eventService = eventService;
    }

    @GetMapping("/incidents")
    public SseEmitter streamIncidents() {
        return eventService.subscribe();
    }
}