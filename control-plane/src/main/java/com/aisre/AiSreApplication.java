package com.aisre;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AiSreApplication {

    public static void main(String[] args) {
        SpringApplication.run(AiSreApplication.class, args);
    }
}