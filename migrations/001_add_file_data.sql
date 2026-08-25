-- Migration 001: store uploaded PDF files inside the database.
-- Run this ONLY if you applied schema_postgres.sql before 2026-08-19
-- (fresh installs already include the column). Safe to run twice.

ALTER TABLE memos ADD COLUMN IF NOT EXISTS file_data BYTEA;
