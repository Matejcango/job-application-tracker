"""Job Application Tracker - Flask application."""
import json
import os
import re
from collections import Counter
from datetime import date, datetime

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import execute, query
from matcher import parse_skills, rank_jobs

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]
STATUS_COLORS = {
    "Applied": "secondary", "Screening": "info", "Interview": "primary",
    "Offer": "success", "Rejected": "danger", "Withdrawn": "dark",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(value):
    """Decode a JSON column value (str/bytes/dict/None) into a dict."""
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def clean(form, field):
    """Return a stripped form value, or None if blank."""
    value = (form.get(field) or "").strip()
    return value or None


def parse_int(form, field, label, errors, minimum=None):
    value = clean(form, field)
    if value is None:
        return None
    try:
        number = int(value.replace(",", "").replace("$", ""))
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if minimum is not None and number < minimum:
        errors.append(f"{label} must be at least {minimum}.")
    return number


def parse_date(form, field, label, errors, required=False):
    value = clean(form, field)
    if value is None:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} must be a valid date (YYYY-MM-DD).")
        return None


def check_url(value, label, errors):
    if value and not re.match(r"^https?://", value, re.I):
        errors.append(f"{label} must start with http:// or https://")


def set_or_remove(data, key, value):
    """Set a key in a JSON dict, or remove it when the value is empty."""
    if value in (None, "", []):
        data.pop(key, None)
    else:
        data[key] = value


def to_json(data):
    return json.dumps(data) if data else None


def company_choices():
    return query("SELECT company_id, company_name FROM companies ORDER BY company_name")


def get_or_404(sql, record_id):
    row = query(sql, (record_id,), one=True)
    if row is None:
        abort(404)
    return row


# Jinja globals are visible inside imported macros too (context processors are not)
app.jinja_env.globals["STATUS_COLORS"] = STATUS_COLORS


@app.context_processor
def inject_globals():
    return {"today": date.today().isoformat()}


@app.template_filter("money")
def money(value):
    return f"${value:,.0f}" if value is not None else ""


@app.errorhandler(mysql.connector.Error)
def handle_db_error(err):
    return render_template("error.html", title="Database error", message=str(err)), 500


@app.errorhandler(404)
def handle_not_found(err):
    return render_template("error.html", title="Not found",
                           message="That record does not exist (it may have been deleted)."), 404


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    counts = query("""
        SELECT (SELECT COUNT(*) FROM companies)    AS companies,
               (SELECT COUNT(*) FROM jobs)         AS jobs,
               (SELECT COUNT(*) FROM applications) AS applications,
               (SELECT COUNT(*) FROM contacts)     AS contacts
    """, one=True)

    status_rows = query("SELECT status, COUNT(*) AS total FROM applications GROUP BY status")
    by_status = {s: 0 for s in STATUSES}
    for row in status_rows:
        by_status[row["status"]] = row["total"]

    total = counts["applications"] or 0
    responded = total - by_status["Applied"] - by_status["Withdrawn"]
    response_rate = round(100 * responded / total) if total else 0

    recent = query("""
        SELECT a.application_id, a.application_date, a.status,
               j.job_title, c.company_name
        FROM applications a
        JOIN jobs j      ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
        LIMIT 5
    """)

    remote_jobs = query("""
        SELECT COUNT(*) AS total FROM jobs
        WHERE requirements->>'$.remote_option' = 'true'
    """, one=True)["total"]

    skill_counter = Counter()
    for row in query("SELECT requirements FROM jobs WHERE requirements IS NOT NULL"):
        for skill in load_json(row["requirements"]).get("required_skills", []):
            skill_counter[str(skill).strip()] += 1
    top_skills = skill_counter.most_common(8)

    return render_template("dashboard.html", counts=counts, by_status=by_status,
                           response_rate=response_rate, recent=recent,
                           remote_jobs=remote_jobs, top_skills=top_skills)


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

def validate_company(form):
    errors = []
    data = {f: clean(form, f) for f in
            ("company_name", "industry", "website", "city", "state", "notes")}
    if not data["company_name"]:
        errors.append("Company name is required.")
    check_url(data["website"], "Website", errors)
    return data, errors


@app.route("/companies")
def companies():
    search = (request.args.get("q") or "").strip()
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)     AS job_count,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = ()
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s"
        like = f"%{search}%"
        params = (like, like, like)
    sql += " ORDER BY c.company_name"
    return render_template("companies.html", companies=query(sql, params), search=search)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", company_id)
    jobs = query("SELECT * FROM jobs WHERE company_id = %s ORDER BY date_posted DESC", (company_id,))
    contacts = query("SELECT * FROM contacts WHERE company_id = %s ORDER BY contact_name", (company_id,))
    return render_template("company_detail.html", company=company, jobs=jobs, contacts=contacts)


@app.route("/companies/add", methods=["GET", "POST"])
def company_add():
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if not errors:
            new_id = execute("""
                INSERT INTO companies (company_name, industry, website, city, state, notes)
                VALUES (%(company_name)s, %(industry)s, %(website)s, %(city)s, %(state)s, %(notes)s)
            """, data)
            flash(f"Added company '{data['company_name']}'.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
        for e in errors:
            flash(e, "danger")
        return render_template("company_form.html", company=data, action="Add")
    return render_template("company_form.html", company={}, action="Add")


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", company_id)
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if not errors:
            data["company_id"] = company_id
            execute("""
                UPDATE companies SET company_name=%(company_name)s, industry=%(industry)s,
                       website=%(website)s, city=%(city)s, state=%(state)s, notes=%(notes)s
                WHERE company_id=%(company_id)s
            """, data)
            flash("Company updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        for e in errors:
            flash(e, "danger")
        company = {**data, "company_id": company_id}
    return render_template("company_form.html", company=company, action="Edit")


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = get_or_404("SELECT company_name FROM companies WHERE company_id = %s", company_id)
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
    flash(f"Deleted '{company['company_name']}' and its jobs, applications and contacts.", "warning")
    return redirect(url_for("companies"))


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

JOB_SELECT = """
    SELECT j.*, c.company_name,
           (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count
    FROM jobs j JOIN companies c ON j.company_id = c.company_id
"""


def job_form_values(job):
    """Flatten a job row (with JSON requirements) into form field values."""
    reqs = load_json(job.get("requirements"))
    return {
        **job,
        "required_skills": ", ".join(reqs.get("required_skills", [])),
        "preferred_skills": ", ".join(reqs.get("preferred_skills", [])),
        "education": reqs.get("education", ""),
        "experience_years": reqs.get("experience_years", ""),
        "remote_option": bool(reqs.get("remote_option")),
    }


def validate_job(form, existing_requirements=None):
    errors = []
    data = {
        "company_id": parse_int(form, "company_id", "Company", errors),
        "job_title": clean(form, "job_title"),
        "job_type": clean(form, "job_type"),
        "salary_min": parse_int(form, "salary_min", "Minimum salary", errors, minimum=0),
        "salary_max": parse_int(form, "salary_max", "Maximum salary", errors, minimum=0),
        "job_url": clean(form, "job_url"),
        "date_posted": parse_date(form, "date_posted", "Date posted", errors),
    }
    if not data["company_id"]:
        errors.append("Please choose a company.")
    if not data["job_title"]:
        errors.append("Job title is required.")
    if data["job_type"] not in JOB_TYPES:
        errors.append("Please choose a valid job type.")
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")
    check_url(data["job_url"], "Job URL", errors)

    # Build the JSON requirements, keeping any extra keys added outside the form.
    reqs = dict(existing_requirements or {})
    set_or_remove(reqs, "required_skills", parse_skills(form.get("required_skills")))
    set_or_remove(reqs, "preferred_skills", parse_skills(form.get("preferred_skills")))
    set_or_remove(reqs, "education", clean(form, "education"))
    set_or_remove(reqs, "experience_years",
                  parse_int(form, "experience_years", "Experience (years)", errors, minimum=0))
    reqs["remote_option"] = form.get("remote_option") == "on"
    data["requirements"] = to_json(reqs)

    # Values for re-displaying the form if validation fails
    form_values = {**data, **{k: form.get(k, "") for k in
                              ("required_skills", "preferred_skills", "education",
                               "experience_years", "salary_min", "salary_max", "date_posted")},
                   "remote_option": reqs["remote_option"]}
    return data, errors, form_values


@app.route("/jobs")
def jobs():
    search = (request.args.get("q") or "").strip()
    job_type = request.args.get("type") or ""
    sql, params, where = JOB_SELECT, [], []
    if search:
        where.append("(j.job_title LIKE %s OR c.company_name LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if job_type in JOB_TYPES:
        where.append("j.job_type = %s")
        params.append(job_type)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    rows = query(sql, params)
    for row in rows:
        row["req"] = load_json(row["requirements"])
    return render_template("jobs.html", jobs=rows, search=search,
                           job_type=job_type, job_types=JOB_TYPES)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(JOB_SELECT + " WHERE j.job_id = %s", job_id)
    job["req"] = load_json(job["requirements"])
    apps = query("SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC", (job_id,))
    return render_template("job_detail.html", job=job, applications=apps)


@app.route("/jobs/add", methods=["GET", "POST"])
def job_add():
    if request.method == "POST":
        data, errors, form_values = validate_job(request.form)
        if not errors:
            new_id = execute("""
                INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                                  job_url, date_posted, requirements)
                VALUES (%(company_id)s, %(job_title)s, %(job_type)s, %(salary_min)s, %(salary_max)s,
                        %(job_url)s, %(date_posted)s, %(requirements)s)
            """, data)
            flash(f"Added job '{data['job_title']}'.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
        for e in errors:
            flash(e, "danger")
        job = form_values
    else:
        job = {"company_id": request.args.get("company_id", type=int), "job_type": "Full-time"}
    return render_template("job_form.html", job=job, action="Add",
                           companies=company_choices(), job_types=JOB_TYPES)


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    existing = get_or_404("SELECT * FROM jobs WHERE job_id = %s", job_id)
    if request.method == "POST":
        data, errors, form_values = validate_job(request.form, load_json(existing["requirements"]))
        if not errors:
            data["job_id"] = job_id
            execute("""
                UPDATE jobs SET company_id=%(company_id)s, job_title=%(job_title)s,
                       job_type=%(job_type)s, salary_min=%(salary_min)s, salary_max=%(salary_max)s,
                       job_url=%(job_url)s, date_posted=%(date_posted)s, requirements=%(requirements)s
                WHERE job_id=%(job_id)s
            """, data)
            flash("Job updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        for e in errors:
            flash(e, "danger")
        job = {**form_values, "job_id": job_id}
    else:
        job = job_form_values(existing)
    return render_template("job_form.html", job=job, action="Edit",
                           companies=company_choices(), job_types=JOB_TYPES)


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = get_or_404("SELECT job_title FROM jobs WHERE job_id = %s", job_id)
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    flash(f"Deleted job '{job['job_title']}' and its applications.", "warning")
    return redirect(url_for("jobs"))


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

APP_SELECT = """
    SELECT a.*, j.job_title, j.company_id, c.company_name
    FROM applications a
    JOIN jobs j      ON a.job_id = j.job_id
    JOIN companies c ON j.company_id = c.company_id
"""
INTERVIEW_FIELDS = ("interviewers", "technical_questions", "interview_rounds",
                    "rating", "offer_amount", "feedback", "next_steps")


def job_choices():
    return query("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j JOIN companies c ON j.company_id = c.company_id
        ORDER BY c.company_name, j.job_title
    """)


def application_form_values(row):
    idata = load_json(row.get("interview_data"))
    values = {**row}
    for key in INTERVIEW_FIELDS:
        value = idata.get(key, "")
        values[key] = ", ".join(map(str, value)) if isinstance(value, list) else value
    return values


def validate_application(form, existing_interview=None):
    errors = []
    data = {
        "job_id": parse_int(form, "job_id", "Job", errors),
        "application_date": parse_date(form, "application_date", "Application date",
                                       errors, required=True),
        "status": clean(form, "status"),
        "resume_version": clean(form, "resume_version"),
        "cover_letter_sent": form.get("cover_letter_sent") == "on",
    }
    if not data["job_id"]:
        errors.append("Please choose a job.")
    if data["status"] not in STATUSES:
        errors.append("Please choose a valid status.")
    if data["application_date"] and data["application_date"] > date.today():
        errors.append("Application date cannot be in the future.")

    idata = dict(existing_interview or {})
    set_or_remove(idata, "interviewers", parse_skills(form.get("interviewers")))
    set_or_remove(idata, "technical_questions", parse_skills(form.get("technical_questions")))
    set_or_remove(idata, "interview_rounds",
                  parse_int(form, "interview_rounds", "Interview rounds", errors, minimum=0))
    rating = parse_int(form, "rating", "Rating", errors, minimum=1)
    if rating is not None and rating > 5:
        errors.append("Rating must be between 1 and 5.")
    set_or_remove(idata, "rating", rating)
    set_or_remove(idata, "offer_amount",
                  parse_int(form, "offer_amount", "Offer amount", errors, minimum=0))
    set_or_remove(idata, "feedback", clean(form, "feedback"))
    set_or_remove(idata, "next_steps", clean(form, "next_steps"))
    data["interview_data"] = to_json(idata)

    form_values = {**data, **{k: form.get(k, "") for k in INTERVIEW_FIELDS},
                   "application_date": form.get("application_date", "")}
    return data, errors, form_values


@app.route("/applications")
def applications():
    status = request.args.get("status") or ""
    sql, params = APP_SELECT, ()
    if status in STATUSES:
        sql += " WHERE a.status = %s"
        params = (status,)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    rows = query(sql, params)
    for row in rows:
        row["idata"] = load_json(row["interview_data"])
    return render_template("applications.html", applications=rows,
                           status=status, statuses=STATUSES)


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    row = get_or_404(APP_SELECT + " WHERE a.application_id = %s", application_id)
    row["idata"] = load_json(row["interview_data"])
    return render_template("application_detail.html", app_row=row)


@app.route("/applications/add", methods=["GET", "POST"])
def application_add():
    if request.method == "POST":
        data, errors, form_values = validate_application(request.form)
        if not errors:
            new_id = execute("""
                INSERT INTO applications (job_id, application_date, status, resume_version,
                                          cover_letter_sent, interview_data)
                VALUES (%(job_id)s, %(application_date)s, %(status)s, %(resume_version)s,
                        %(cover_letter_sent)s, %(interview_data)s)
            """, data)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
        for e in errors:
            flash(e, "danger")
        app_row = form_values
    else:
        app_row = {"job_id": request.args.get("job_id", type=int), "status": "Applied",
                   "application_date": date.today().isoformat()}
    return render_template("application_form.html", app_row=app_row, action="Add",
                           jobs=job_choices(), statuses=STATUSES)


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    existing = get_or_404("SELECT * FROM applications WHERE application_id = %s", application_id)
    if request.method == "POST":
        data, errors, form_values = validate_application(
            request.form, load_json(existing["interview_data"]))
        if not errors:
            data["application_id"] = application_id
            execute("""
                UPDATE applications SET job_id=%(job_id)s, application_date=%(application_date)s,
                       status=%(status)s, resume_version=%(resume_version)s,
                       cover_letter_sent=%(cover_letter_sent)s, interview_data=%(interview_data)s
                WHERE application_id=%(application_id)s
            """, data)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        for e in errors:
            flash(e, "danger")
        app_row = {**form_values, "application_id": application_id}
    else:
        app_row = application_form_values(existing)
    return render_template("application_form.html", app_row=app_row, action="Edit",
                           jobs=job_choices(), statuses=STATUSES)


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    get_or_404("SELECT application_id FROM applications WHERE application_id = %s", application_id)
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted.", "warning")
    return redirect(url_for("applications"))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

CONTACT_SELECT = """
    SELECT k.*, c.company_name FROM contacts k
    JOIN companies c ON k.company_id = c.company_id
"""


def validate_contact(form):
    errors = []
    data = {f: clean(form, f) for f in
            ("contact_name", "title", "email", "phone", "linkedin_url", "notes")}
    data["company_id"] = parse_int(form, "company_id", "Company", errors)
    if not data["company_id"]:
        errors.append("Please choose a company.")
    if not data["contact_name"]:
        errors.append("Contact name is required.")
    if data["email"] and not EMAIL_RE.match(data["email"]):
        errors.append("Email address is not valid.")
    if data["phone"] and not re.match(r"^[0-9+()\-.\s]{7,20}$", data["phone"]):
        errors.append("Phone number may only contain digits, spaces and + ( ) - .")
    check_url(data["linkedin_url"], "LinkedIn URL", errors)
    return data, errors


@app.route("/contacts")
def contacts():
    search = (request.args.get("q") or "").strip()
    sql, params = CONTACT_SELECT, ()
    if search:
        sql += " WHERE k.contact_name LIKE %s OR c.company_name LIKE %s OR k.title LIKE %s"
        like = f"%{search}%"
        params = (like, like, like)
    sql += " ORDER BY k.contact_name"
    return render_template("contacts.html", contacts=query(sql, params), search=search)


@app.route("/contacts/add", methods=["GET", "POST"])
def contact_add():
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if not errors:
            execute("""
                INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
                VALUES (%(company_id)s, %(contact_name)s, %(title)s, %(email)s, %(phone)s,
                        %(linkedin_url)s, %(notes)s)
            """, data)
            flash(f"Added contact '{data['contact_name']}'.", "success")
            return redirect(url_for("contacts"))
        for e in errors:
            flash(e, "danger")
        contact = data
    else:
        contact = {"company_id": request.args.get("company_id", type=int)}
    return render_template("contact_form.html", contact=contact, action="Add",
                           companies=company_choices())


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404("SELECT * FROM contacts WHERE contact_id = %s", contact_id)
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if not errors:
            data["contact_id"] = contact_id
            execute("""
                UPDATE contacts SET company_id=%(company_id)s, contact_name=%(contact_name)s,
                       title=%(title)s, email=%(email)s, phone=%(phone)s,
                       linkedin_url=%(linkedin_url)s, notes=%(notes)s
                WHERE contact_id=%(contact_id)s
            """, data)
            flash("Contact updated.", "success")
            return redirect(url_for("contacts"))
        for e in errors:
            flash(e, "danger")
        contact = {**data, "contact_id": contact_id}
    return render_template("contact_form.html", contact=contact, action="Edit",
                           companies=company_choices())


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = get_or_404("SELECT contact_name FROM contacts WHERE contact_id = %s", contact_id)
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    flash(f"Deleted contact '{contact['contact_name']}'.", "warning")
    return redirect(url_for("contacts"))


# ---------------------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------------------

@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    skills_text = request.values.get("skills", "")
    show_all = request.values.get("show_all") == "on"
    user_skills = parse_skills(skills_text)
    results, unmatched = None, 0

    if request.method == "POST" or skills_text:
        if not user_skills:
            flash("Enter at least one skill, separated by commas.", "danger")
        else:
            rows = query("""
                SELECT j.job_id, j.job_title, j.job_type, j.salary_min, j.salary_max,
                       j.requirements, c.company_name
                FROM jobs j JOIN companies c ON j.company_id = c.company_id
                WHERE j.requirements IS NOT NULL
            """)
            for row in rows:
                row["requirements"] = load_json(row["requirements"])
            results = rank_jobs(user_skills, rows, include_zero=show_all)
            with_reqs = sum(1 for r in rows if r["requirements"].get("required_skills"))
            unmatched = with_reqs - len([r for r in results if r["percent"] > 0])

    return render_template("job_match.html", skills_text=skills_text, user_skills=user_skills,
                           results=results, unmatched=unmatched, show_all=show_all)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
