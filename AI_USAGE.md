# AI Usage

## Tools Used

- **Claude Code** (VS Code extension, Claude Opus 5.5)
- **ChatGPT**

## How AI Was Used

- **Code generation:** Claude generated the initial implementation from the project specification: the MySQL schema and sample data, the Flask routes and database layer, the Jinja/Bootstrap templates, the Job Match algorithm (`matcher.py`), and the unit tests.
- **Testing:** Claude ran the app against a temporary local MySQL instance, loading `schema.sql` and the Assignment 7 script, and ran automated checks against every page.
- **Demo video:** Claude scripted and recorded the demo video. A Playwright script drove the app in the browser, on-screen captions explained each step, and MySQL query windows showed each change in the database. OBS Studio did the screen recording.

## Key Prompts

1. Generate the Flask project from the provided project specification, following its required folder structure and features.
2. Review and test the app end to end, and fix any bugs found.
3. Record a 3–7 minute demo covering the client, server, and database.

## What Worked Well

- **CRUD boilerplate:** consistent list, detail, add, edit, and delete pages for all four tables, using parameterized queries (`%s`) to prevent SQL injection.
- **JSON columns in forms:** skills and interview details are entered as normal form fields and saved as JSON; extra keys added in Workbench are kept when a record is edited.
- **Testable Job Match:** the matching logic lives in its own module with unit tests that reproduce the specification's example (100% for 3 of 3 skills, 67% with one missing).

## Bugs Found and Fixed

- **Navbar highlighting:** the "Jobs" tab was highlighted on the Job Match page because both route names start with `job_`.
- **Status badge colors:** imported Jinja macros cannot see context-processor variables, so the color mapping was moved to a Jinja global.
- **Empty skills placeholder:** the "—" fallback never showed because the macro output contained whitespace and was never considered empty.

## My Contributions and Decisions

- Reviewed the generated code to understand the request flow (route → `database.py` → MySQL → template).
- Structured the Git history as logical commits (schema → database layer → matching algorithm → Flask app → docs) and created and pushed the GitHub repository myself.
- Kept credentials out of the repository: the database password lives in `.env`, which is excluded by `.gitignore`.

## Lessons Learned

- **Generated code that looks correct can still be wrong.** All three template bugs looked fine on reading; they only appeared when pages were rendered and tested.
- **Test against a real database.** Unit tests covered the matching logic, but only end-to-end tests against MySQL confirmed that forms, JSON columns, and cascading deletes worked together.
- **AI is fastest at repetitive code**, such as CRUD pages for four tables, but explaining the system still requires understanding how the pieces connect.
- **Credentials never go into an AI chat.** Sign-ins go through official login flows, and secrets stay in uncommitted `.env` files.
