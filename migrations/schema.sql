-- Migration to create students table
-- Run this with: psql $DATABASE_URL -f migrations/schema.sql

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    mothername TEXT,
    fathername TEXT,
    age INTEGER,
    gender TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
