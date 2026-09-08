-- P2-FE-05: evidence.content 4096 varchar -> text（写入端截断导致 JSON 残废）
ALTER TABLE evidence ALTER COLUMN content TYPE text;
