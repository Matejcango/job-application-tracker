# Job Application Tracker

A full-stack web app for tracking a job search: companies, job postings, applications, and contacts. It also has a **Job Match** page that ranks jobs by how well your skills fit them.

**Stack:** MySQL 8 · Python 3 / Flask · HTML + Bootstrap 5 · JSON columns

## Features

- **Dashboard:** record counts, applications by status, response rate, recent applications, the most-requested skills, and how many jobs are remote.
- **Full CRUD for all 4 tables:** list (with search/filter), detail, add, edit, and delete (with a confirmation prompt) for companies, jobs, applications, and contacts.
- **JSON columns:**
  - `jobs.requirements` stores required and preferred skills, education, experience, and remote option.
  - `applications.interview_data` stores interview rounds, interviewers, questions, feedback, rating, offer amount, and next steps.
  - Both are edited through normal form fields. Keys the forms don't manage (for example ones added with `JSON_SET` in Workbench) are kept when you save.
- **Job Match:** enter your skills (comma-separated) and see jobs ranked by the percentage of *required* skills you have. Each result lists the matching and missing skills, plus a bonus for matching preferred skills.
- **Validation:** required fields, salary min ≤ max, valid dates (no future application dates), email/phone/URL format, and a 1–5 rating. Errors appear as messages and your input is kept.

## Setup

### 1. Prerequisites

- Python 3.10+
- MySQL Server 8.0 (plus MySQL Workbench, optional)

### 2. Create the database

> ⚠️ `schema.sql` **drops and recreates** the `job_tracker` database. Back up anything you want to keep first.

In MySQL Workbench: *File → Open SQL Script → schema.sql*, then run it (⚡).
Or from a terminal:

```bash
mysql -u root -p < schema.sql
```

This creates the 4 tables with foreign keys and loads sample data.

### 3. Install Python dependencies

```bash
cd job_tracker
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure your database password

Copy `.env.example` to `.env` and set `DB_PASSWORD` to your MySQL password:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

`.env` is in `.gitignore`, so your password is never committed.

### 5. Run

```bash
python app.py
```

Open <http://127.0.0.1:5000>.

### Run the tests

```bash
pip install pytest
python -m pytest -q
```

## Project structure

```
job_tracker/
├── app.py              # Flask routes, validation, CRUD for all tables
├── database.py         # MySQL connection + query/execute helpers
├── matcher.py          # Job Match algorithm (no Flask/DB, unit-tested)
├── schema.sql          # Creates the database, tables, and sample data
├── requirements.txt
├── .env.example        # Copy to .env with your DB credentials
├── templates/
│   ├── base.html               # Layout, navbar, flash messages
│   ├── _macros.html            # Reusable form fields / buttons
│   ├── dashboard.html
│   ├── companies.html  company_detail.html  company_form.html
│   ├── jobs.html       job_detail.html      job_form.html
│   ├── applications.html application_detail.html application_form.html
│   ├── contacts.html   contact_form.html
│   ├── job_match.html
│   └── error.html
├── static/style.css
├── tests/test_matcher.py
├── AI_USAGE.md
└── README.md
```

## Database design

| Table | Key columns | Relationships |
|---|---|---|
| `companies` | company_id, company_name, industry, website, city, state, notes | parent of jobs and contacts |
| `jobs` | job_id, job_title, job_type (ENUM), salary_min/max, job_url, date_posted, **requirements (JSON)** | FK → companies |
| `applications` | application_id, application_date, status (ENUM), resume_version, cover_letter_sent, **interview_data (JSON)** | FK → jobs |
| `contacts` | contact_id, contact_name, title, email, phone, linkedin_url, notes | FK → companies |

The foreign keys use `ON DELETE CASCADE`. Deleting a company removes its jobs, those jobs' applications, and its contacts, and the delete confirmation tells you this before anything is removed. A `CHECK` constraint enforces `salary_min <= salary_max`.

## How Job Match works

1. Your input is split on commas, trimmed, and de-duplicated, ignoring upper/lower case.
2. For each job with `required_skills` in its `requirements` JSON:
   `match % = (required skills you have) / (total required skills) × 100`
3. Jobs are sorted by match %, then by how many *preferred* skills you have, then by title.
4. Jobs with a 0% match are hidden unless you tick **Include 0% matches**.

Example from the spec: with skills `Python, SQL, Flask`, a job that requires Python/SQL/Flask scores **100% (3/3)**, and one that requires Python/SQL/Tableau scores **67% (2/3)** with **Missing: Tableau**.
