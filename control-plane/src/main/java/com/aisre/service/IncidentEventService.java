package com.aisre.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * P2-CP-19: SSE 事件广播——订阅者心跳（15s，防中间层断链）+ 完成/超时/错误清理。
 * ponytail: 进程内广播单实例够用；多实例部署时改 Redis pub/sub 扇出（订阅端不变）。
 */
@Service
public class IncidentEventService {

    private static final Logger log = LoggerFactory.getLogger(IncidentEventService.class);

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(0L);
        emitters.add(emitter);
        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        // P2-CP-19: 连接异常也要清理（此前只有 completion/timeout）
        emitter.onError(e -> {
            log.debug("sse emitter error: {}", String.valueOf(e));
            emitters.remove(emitter);
        });
        return emitter;
    }

    /** 心跳：保持连接活性并让前端能探测断线。 */
    @Scheduled(fixedDelay = 15000)
    public void heartbeat() {
        send(emitter -> emitter.send(SseEmitter.event().name("heartbeat").data("ping")));
    }

    public void publish(Long incidentId, String event, Object data) {
        send(emitter -> emitter.send(SseEmitter.event()
                .name(event)
                .id(String.valueOf(incidentId))
                .data(data)));
    }

    private interface SendOp {
        void run(SseEmitter emitter) throws IOException;
    }

    private void send(SendOp op) {
        for (SseEmitter emitter : emitters) {
            try {
                op.run(emitter);
            } catch (IOException | IllegalStateException e) {
                emitters.remove(emitter);
            }
        }
    }
}