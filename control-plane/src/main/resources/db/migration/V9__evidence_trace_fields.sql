-- P2-AR-09: 证据溯源字段
ALTER TABLE evidence ADD COLUMN query VARCHAR(1024);
ALTER TABLE evidence ADD COLUMN time_range VARCHAR(64);
