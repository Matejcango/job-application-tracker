"""Unit tests for the Job Match algorithm. Run with:  python -m pytest -q"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matcher import match_job, parse_skills, rank_jobs  # noqa: E402

JOBS = [
    {"job_id": 1, "job_title": "Software Developer", "company_name": "TechCorp",
     "requirements": {"required_skills": ["Python", "SQL", "Flask"],
                      "preferred_skills": ["Docker"]}},
    {"job_id": 2, "job_title": "Data Analyst", "company_name": "DataCo",
     "requirements": {"required_skills": ["Python", "SQL", "Tableau"]}},
    {"job_id": 3, "job_title": "Designer", "company_name": "ArtCo",
     "requirements": {"required_skills": ["Figma", "Photoshop"]}},
    {"job_id": 4, "job_title": "No Reqs", "company_name": "X", "requirements": {}},
]


def test_parse_skills_trims_dedupes_and_keeps_order():
    assert parse_skills(" Python, sql ,,Flask,python\nGit ") == ["Python", "sql", "Flask", "Git"]
    assert parse_skills("") == []
    assert parse_skills(None) == []


def test_match_job_is_case_insensitive():
    result = match_job(["python", "SQL"], ["Python", "SQL", "Tableau"])
    assert result["matched"] == ["Python", "SQL"]
    assert result["missing"] == ["Tableau"]
    assert result["percent"] == 67


def test_match_job_with_no_required_skills():
    assert match_job(["Python"], [])["percent"] == 0


def test_rank_jobs_matches_spec_example():
    results = rank_jobs(["Python", "SQL", "Flask"], JOBS)
    assert [(r["job_title"], r["percent"]) for r in results] == [
        ("Software Developer", 100),
        ("Data Analyst", 67),
    ]
    assert results[1]["missing"] == ["Tableau"]


def test_rank_jobs_include_zero_skips_jobs_without_requirements():
    results = rank_jobs(["Python"], JOBS, include_zero=True)
    titles = [r["job_title"] for r in results]
    assert "Designer" in titles
    assert "No Reqs" not in titles


def test_preferred_skills_break_ties():
    jobs = [
        {"job_id": 1, "job_title": "A", "requirements": {"required_skills": ["SQL"]}},
        {"job_id": 2, "job_title": "B", "requirements": {"required_skills": ["SQL"],
                                                          "preferred_skills": ["Docker"]}},
    ]
    results = rank_jobs(["SQL", "Docker"], jobs)
    assert [r["job_title"] for r in results] == ["B", "A"]
    assert results[0]["preferred_matched"] == ["Docker"]
