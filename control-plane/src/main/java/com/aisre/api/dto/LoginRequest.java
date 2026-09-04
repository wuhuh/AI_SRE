package com.aisre.api.dto;

public record LoginRequest(
        String username,
        String password
) {
}