# AI Usage Documentation

> **Note to self before submitting:** the factual parts below describe what the AI actually produced. Rewrite the sections marked ✏️ in your own words, based on what *you* reviewed, changed, and learned. The rubric grades honest reflection, not a polished template.

## Tools Used

- **Claude (Claude Code, Opus 5.5 model)** generated the initial project: the database schema, Flask routes, templates, the Job Match algorithm, and its unit tests.
- ✏️ *(List any other tools you used, e.g. ChatGPT for explaining errors, plus anything you used Claude for afterwards: debugging, explanations, etc.)*

## Key Prompts

1. "Do Assignment 7 and the project," with the Assignment 7 handout and the Project Specification (.docx) as context.
2. ✏️ *(Add the follow-up prompts you use: debugging, changes, explanations. For example:)*
   - "Explain how `JSON_SET` keeps the other keys in a JSON column."
   - "Why does my Flask app say `Access denied for user 'root'@'localhost'`?"

## What Worked Well

- **CRUD boilerplate:** the AI produced consistent list/detail/add/edit/delete routes for all four tables quickly, using parameterized queries (`%s` placeholders) to prevent SQL injection.
- **JSON columns in forms:** it mapped the `requirements` and `interview_data` JSON columns to ordinary form fields (comma-separated skill lists, numbers, checkboxes) instead of making users type raw JSON. When a record is edited, the existing JSON is merged, so keys added in Workbench with `JSON_SET` (like `offer_amount`) aren't lost.
- **Job Match algorithm:** it kept the matching logic in its own module (`matcher.py`), separate from Flask and MySQL, so it can be unit-tested. The tests reproduce the spec's example (100% and 67%, Missing: Tableau).
- **Sample data:** it lined up the seed data with Assignment 7 (applications 2 and 5, jobs 1 and 3 hold the same JSON as the handout).

## What I Modified / Reviewed

Changes made during generation, after reviewing the first draft:
- Fixed navbar highlighting so the "Jobs" tab doesn't light up on the Job Match page (both routes start with `job_`).
- Made the status-color mapping a Jinja *global*, because macros imported with `{% from ... import %}` can't see context-processor variables.
- Replaced a `{{ macro() or '—' }}` fallback that never showed, because the macro's output contains whitespace and is therefore never "empty".

✏️ *Add your own changes here, for example:*
- *Changed the sample data to companies/jobs I'm actually applying to*
- *Adjusted styling/colors*
- *Added or removed a validation rule*
- *Anything you fixed after testing it yourself*

## Lessons Learned

✏️ *Write 3–5 bullet points in your own words. Some prompts to think about:*
- *Did the AI-generated code run the first time? What broke, and how did you find out?*
- *What did you have to understand before you could explain the code in your video?*
- *Where was AI most useful (boilerplate, SQL, explanations) and least useful?*
- *Why does testing AI output matter, e.g. the template bugs above that looked correct?*
