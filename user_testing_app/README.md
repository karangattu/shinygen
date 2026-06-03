# Dashboard Ranker — Interactive Tier List

An interactive web application designed to collect user feedback on LLM-generated dashboard screenshots. The app presents screenshots anonymously, tracks evaluation progress, prompts a structured feedback modal to collect 2-word critiques, and records user responses in a Supabase database table.

## 1. Database Table Setup

Execute the SQL script below in your **Supabase SQL Editor** to create the table and enable realtime updates:

```sql
CREATE TABLE IF NOT EXISTS dashboard_tiered_rankings_python (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    session_id TEXT NOT NULL,
    dashboard_id TEXT NOT NULL,
    model TEXT NOT NULL,
    arm TEXT NOT NULL,
    tier TEXT NOT NULL,
    feedback_words TEXT NOT NULL,
    top_reason TEXT,
    bottom_reason TEXT,
    framework TEXT DEFAULT 'python' NOT NULL
);

-- Enable Row Level Security (RLS)
ALTER TABLE dashboard_tiered_rankings_python ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts from client-side JS
CREATE POLICY "Allow anonymous inserts" 
ON dashboard_tiered_rankings_python 
FOR INSERT 
TO anon 
WITH CHECK (true);

-- Allow anonymous reads
CREATE POLICY "Allow anonymous reads" 
ON dashboard_tiered_rankings_python 
FOR SELECT 
TO anon 
USING (true);

-- Enable Realtime
alter publication supabase_realtime add table dashboard_tiered_rankings_python;
```

## 2. How to Run Locally

Run a lightweight HTTP server to load the app:

```bash
python3 -m http.server 8080 --directory user_testing_app
```

Then open: **[http://localhost:8080/](http://localhost:8080/)**

## 3. Database Migration
To support R Shiny rankings alongside Python, run this migration query in your Supabase SQL Editor:
```sql
ALTER TABLE dashboard_tiered_rankings_python ADD COLUMN IF NOT EXISTS framework TEXT DEFAULT 'python' NOT NULL;
```
