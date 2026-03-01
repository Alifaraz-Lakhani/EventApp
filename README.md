# ⚡ EventApp — College Event Management Platform

A web-based platform that centralizes college events (hackathons, workshops, seminars), enabling students to discover, participate, find teammates, and receive AI-powered recommendations.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

### For Students
- **Event Discovery** — Browse upcoming events with category tags, mode badges, and countdown timers
- **One-Click Participation** — Register/unenroll from events instantly
- **Team Pool** — Find teammates by skills and roles for team-based events
- **Smart Recommendations** — AI-inspired interest prediction engine scores your preferences and suggests events
- **Notifications** — Get alerts for team requests, recommendations (>75% match), and event reminders

### For Admins / Organizers
- **Event CRUD** — Create, edit, and soft-delete events with full detail management
- **Participation Tracking** — See enrollment counts per event on the dashboard

### General
- **UID-Based Auth** — Students login with college UID; admins with prefixed IDs
- **Premium Dark Theme** — Glassmorphic UI with gradient accents, micro-animations, and responsive design

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, Jinja2, Vanilla CSS (custom dark design system) |
| **Backend** | Python, Flask |
| **Database** | PostgreSQL via Supabase |
| **DB Driver** | psycopg2 |

---

## 📸 Screenshots

<details>
<summary>Click to expand</summary>

### Login Page
> Glassmorphic card with gradient branding

### Student Dashboard
> Event cards with category/mode tags, recommendations section

### My Events
> Enrolled events with live countdown timers

### Notifications
> Typed alerts — team requests, recommendations, reminders

### Admin Dashboard
> Data table with participant counts and event management

</details>

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A [Supabase](https://supabase.com) project (free tier works)

### 1. Clone the repo
```bash
git clone https://github.com/Alifaraz-Lakhani/EventApp.git
cd EventApp
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your Supabase credentials and a Flask secret key
```

### 5. Set up the database
Run these SQL statements in the **Supabase SQL Editor**:

```sql
-- Core tables (create these first)
CREATE TABLE users (
    uid        text PRIMARY KEY,
    name       text,
    email      text,
    phone      text,
    role       text,
    created_at timestamp DEFAULT now()
);

CREATE TABLE events (
    id             serial PRIMARY KEY,
    title          text,
    description    text,
    category       text,
    mode           text,
    event_datetime timestamp,
    team_size      int DEFAULT 1,
    created_by     text,
    is_active      bool DEFAULT true,
    created_at     timestamp DEFAULT now()
);

CREATE TABLE participations (
    id        serial PRIMARY KEY,
    user_uid  text REFERENCES users(uid),
    event_id  int REFERENCES events(id),
    joined_at timestamp DEFAULT now(),
    UNIQUE(user_uid, event_id)
);

CREATE TABLE notifications (
    id         serial PRIMARY KEY,
    user_uid   text REFERENCES users(uid),
    title      text,
    message    text,
    type       text,
    is_read    bool DEFAULT false,
    created_at timestamp DEFAULT now()
);

CREATE TABLE team_pool (
    id                serial PRIMARY KEY,
    event_id          int REFERENCES events(id),
    user_uid          text REFERENCES users(uid),
    current_team_size int DEFAULT 1,
    skills            text,
    looking_for_role  text,
    created_at        timestamp DEFAULT now()
);

CREATE TABLE team_requests (
    id            serial PRIMARY KEY,
    from_user_uid text REFERENCES users(uid),
    to_user_uid   text REFERENCES users(uid),
    event_id      int REFERENCES events(id),
    status        text DEFAULT 'pending',
    created_at    timestamp DEFAULT now()
);

CREATE TABLE interest_scores (
    id         serial PRIMARY KEY,
    user_uid   text REFERENCES users(uid),
    category   text NOT NULL,
    score      int NOT NULL DEFAULT 0,
    updated_at timestamp DEFAULT now(),
    UNIQUE(user_uid, category)
);
```

### 6. Run the app
```bash
python app.py
```
Visit **http://127.0.0.1:5000** in your browser.

---

## 📁 Project Structure

```
EventApp/
├── app.py                  # Flask app factory + blueprint registration
├── db.py                   # PostgreSQL (Supabase) connection helper
├── requirements.txt
├── .env.example
│
├── routes/
│   ├── auth.py             # Login/register, logout
│   ├── student.py          # Dashboard, my events, participate/unenroll
│   ├── admin.py            # Event CRUD, participant counts
│   ├── notifications.py    # List, mark read, mark all read
│   ├── teams.py            # Team pool, send/accept/reject requests
│   └── interest.py         # Interest prediction engine, recommendations
│
├── templates/
│   ├── base.html           # Shared layout (navbar, toasts, footer)
│   ├── login.html
│   ├── student_dashboard.html
│   ├── my_events.html      # Countdown timers
│   ├── notifications.html
│   ├── team_pool.html
│   ├── admin_dashboard.html
│   ├── admin_add_event.html
│   └── admin_edit_event.html
│
└── static/css/
    └── style.css           # Full dark theme design system
```

---

## 🧠 Interest Prediction Engine

The engine calculates a **0–100% interest score** per category using:

```
score = 0.5 × category_match + 0.3 × frequency + 0.2 × recency
```

| Component | What It Measures | Max |
|-----------|-----------------|-----|
| **Category Match** | Participations in this category (×25 each) | 100 |
| **Frequency** | Ratio of this category vs total participations | 100 |
| **Recency** | How recently the student participated | 100 |

When a score exceeds **75%**, the student is automatically notified.

---

## 🔮 Future Roadmap

- [ ] Password-based authentication + hashing
- [ ] CSRF protection via `flask-wtf`
- [ ] Email reminders (SMTP / Nodemailer) 24hrs before events
- [ ] Search & filter events by category, mode, date
- [ ] Pagination for large event lists
- [ ] WebSocket real-time notifications
- [ ] WhatsApp integration for reminders
- [ ] QR-based attendance tracking
- [ ] Docker containerization

---

## 📄 License

This project is open source under the [MIT License](LICENSE).

---

<p align="center">
  Built with ⚡ by <a href="https://github.com/Alifaraz-Lakhani">Alifaraz Lakhani</a>
</p>
