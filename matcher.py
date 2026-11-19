"""Skill-matching logic for the Job Match feature.

Kept separate from Flask and MySQL so it can be unit-tested on its own.
"""


def parse_skills(text):
    """Split a comma/newline separated string into a clean, de-duplicated list.

    "Python, sql ,  Flask,python" -> ["Python", "sql", "Flask"]
    """
    if not text:
        return []
    seen = set()
    skills = []
    for part in text.replace("\n", ",").split(","):
        skill = part.strip()
        key = skill.lower()
        if skill and key not in seen:
            seen.add(key)
            skills.append(skill)
    return skills


def match_job(user_skills, required, preferred=None):
    """Compare a user's skills against one job's requirements.

    Matching is case-insensitive. The percentage is based on required
    skills only; preferred skills are reported separately as a bonus.
    """
    have = {s.strip().lower() for s in user_skills if s.strip()}
    required = [s for s in (required or []) if str(s).strip()]
    preferred = [s for s in (preferred or []) if str(s).strip()]

    matched = [s for s in required if str(s).strip().lower() in have]
    missing = [s for s in required if str(s).strip().lower() not in have]
    preferred_matched = [s for s in preferred if str(s).strip().lower() in have]

    percent = round(100 * len(matched) / len(required)) if required else 0
    return {
        "matched": matched,
        "missing": missing,
        "preferred_matched": preferred_matched,
        "required_count": len(required),
        "percent": percent,
    }


def rank_jobs(user_skills, jobs, include_zero=False):
    """Score and rank a list of jobs.

    Each job is a dict containing at least 'job_id', 'job_title' and a
    'requirements' dict (already decoded from JSON). Jobs without any
    required skills are skipped. Results are sorted by match percentage,
    then by number of preferred skills matched, then by job title.
    """
    results = []
    for job in jobs:
        reqs = job.get("requirements") or {}
        required = reqs.get("required_skills") or []
        if not required:
            continue
        score = match_job(user_skills, required, reqs.get("preferred_skills"))
        if score["percent"] == 0 and not include_zero:
            continue
        results.append({**job, **score})

    results.sort(key=lambda r: (-r["percent"], -len(r["preferred_matched"]),
                                r["job_title"].lower()))
    return results
