# DashSwipe — Human vs LLM Dashboard Evaluation

An interactive Tinder-like web application designed to collect user feedback on LLM-generated dashboard screenshots. The app presents screenshots, tracks evaluation progress, prompts a structured glassmorphic feedback form upon card disapproval, and records user responses directly into a Supabase database table.

## Features
- **Tinder Gesture Swipe**: Slide cards left (Disapprove) or right (Approve) with mouse drags or mobile touch swipes.
- **Unified Actions Overlay**: Displays absolute "APPROVE" or "DISAPPROVE" text indicators while cards are being dragged.
- **Detailed Form Triggers**: Swiping left prompts a comprehensive feedback modal to collect precise layout or feature flaws.
- **Analytics Dashboard**: Completing 10 swipes shows local session statistics, including approval rates and most flagged design issues.
- **Direct Supabase Sync**: Connects securely to the database to collect and log swipes.
- **Keyboard Shortcuts**: Use keyboard <kbd>◄</kbd> and <kbd>►</kbd> arrows to swipe cards instantly.

---

## 1. Database Table Setup

To capture human votes, you must create a table named `dashboard_feedback` in your Supabase project.

Copy and paste the SQL script below into your **Supabase SQL Editor** and click **Run**:

```sql
CREATE TABLE IF NOT EXISTS dashboard_feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    screenshot_id TEXT NOT NULL,
    screenshot_url TEXT NOT NULL,
    user_rating TEXT NOT NULL,
    disapproval_reason TEXT,
    disapproval_details TEXT
);

-- Enable Row Level Security (RLS)
ALTER TABLE dashboard_feedback ENABLE ROW LEVEL SECURITY;

-- Create policy to allow anonymous inserts from client-side JS
CREATE POLICY "Allow anonymous inserts" 
ON dashboard_feedback 
FOR INSERT 
TO anon 
WITH CHECK (true);
```

---

## 2. How to Run Locally

Since this is a self-contained, zero-dependency client application, you can run it instantly using any simple HTTP server:

```bash
# Start a lightweight Python server inside the folder
python3 -m http.server 8080 --directory user_testing_app
```

Then open your browser and navigate to:
**[http://localhost:8080/](http://localhost:8080/)**

*Alternatively, you can double-click `index.html` to open it in your browser directly.*
