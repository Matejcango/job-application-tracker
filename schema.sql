-- =====================================================================
-- Job Application Tracker - database creation script
-- WARNING: drops and recreates the job_tracker database.
-- Back up any data you want to keep before running it.
-- =====================================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE job_tracker;

-- ---------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------

CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT
);

CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE,
    CONSTRAINT chk_salary CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);

CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_apps_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contacts_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX idx_jobs_company     ON jobs(company_id);
CREATE INDEX idx_apps_job         ON applications(job_id);
CREATE INDEX idx_apps_status      ON applications(status);
CREATE INDEX idx_contacts_company ON contacts(company_id);

-- ---------------------------------------------------------------------
-- Sample data
-- ---------------------------------------------------------------------

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',        'Software',     'https://techcorp.example.com',   'Austin',  'TX', 'Fast-growing SaaS company'),
('DataCo',          'Analytics',    'https://dataco.example.com',     'Miami',   'FL', 'Data consulting firm'),
('CloudNine',       'Cloud',        'https://cloudnine.example.com',  'Seattle', 'WA', 'AWS partner'),
('HealthBridge',    'Healthcare',   'https://healthbridge.example.com','Orlando','FL', 'Hospital software'),
('FinEdge',         'Finance',      'https://finedge.example.com',    'New York','NY', 'Fintech startup');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer', 'Full-time', 75000, 95000, 'https://techcorp.example.com/jobs/101', '2026-09-01',
 '{"required_skills": ["Python", "SQL", "Git"], "preferred_skills": ["Flask", "Docker", "AWS"], "education": "Bachelor in CS or related field", "experience_years": 2, "remote_option": true}'),
(1, 'Junior Web Developer', 'Full-time', 55000, 70000, 'https://techcorp.example.com/jobs/102', '2026-09-10',
 '{"required_skills": ["HTML", "CSS", "JavaScript"], "preferred_skills": ["React", "Git"], "education": "Associate or Bachelor degree", "experience_years": 0, "remote_option": true}'),
(2, 'Data Analyst', 'Full-time', 60000, 75000, 'https://dataco.example.com/careers/da', '2026-09-15',
 '{"required_skills": ["SQL", "Excel", "Tableau"], "preferred_skills": ["Python", "R"], "education": "Bachelor degree", "experience_years": 1, "remote_option": false}'),
(3, 'Cloud Engineer Intern', 'Internship', 25000, 30000, 'https://cloudnine.example.com/intern', '2026-10-01',
 '{"required_skills": ["Linux", "Python", "AWS"], "preferred_skills": ["Docker", "Terraform"], "education": "Currently enrolled in CS program", "experience_years": 0, "remote_option": false}'),
(4, 'Database Administrator', 'Full-time', 80000, 100000, 'https://healthbridge.example.com/jobs/dba', '2026-10-05',
 '{"required_skills": ["MySQL", "SQL", "Linux"], "preferred_skills": ["Python", "Backup and recovery"], "education": "Bachelor in IT or related field", "experience_years": 3, "remote_option": true}'),
(5, 'Backend Developer (Contract)', 'Contract', 70000, 90000, 'https://finedge.example.com/jobs/be', '2026-10-20',
 '{"required_skills": ["Python", "Flask", "SQL", "REST APIs"], "preferred_skills": ["Docker"], "education": "Any", "experience_years": 2, "remote_option": true}');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-09-05', 'Applied',   'v1-general', TRUE,  NULL),
(3, '2026-09-18', 'Interview', 'v2-data',    TRUE,
 '{"interview_rounds": 2, "interviewers": ["Sarah Johnson", "Mike Chen", "David Brown"], "technical_questions": ["SQL joins", "Python basics", "API design"], "feedback": "Strong technical skills, good communication", "next_steps": "Offer extended!", "offer_amount": 85000}'),
(2, '2026-09-20', 'Rejected',  'v1-general', FALSE, NULL),
(4, '2026-10-03', 'Screening', 'v3-cloud',   TRUE,  NULL),
(5, '2026-10-08', 'Interview', 'v2-data',    TRUE,
 '{"interview_rounds": 1, "interviewers": ["Emily Williams"], "technical_questions": ["Database normalization", "Transaction isolation"], "feedback": "Needs more experience with cloud platforms"}'),
(6, '2026-10-22', 'Offer',     'v4-backend', TRUE,
 '{"interview_rounds": 3, "interviewers": ["Raj Patel"], "technical_questions": ["Flask blueprints", "REST design"], "feedback": "Great culture fit", "next_steps": "Review offer letter", "rating": 5}');

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Sarah Johnson',  'Engineering Manager', 'sarah.johnson@techcorp.example.com', '512-555-0101', 'https://linkedin.com/in/example-sarah', 'Met at career fair'),
(2, 'Mike Chen',      'Senior Data Analyst', 'mike.chen@dataco.example.com',       '305-555-0102', NULL, 'Interviewer for Data Analyst role'),
(3, 'Laura Kim',      'Recruiter',           'laura.kim@cloudnine.example.com',    '206-555-0103', 'https://linkedin.com/in/example-laura', NULL),
(4, 'Emily Williams', 'IT Director',         'emily.w@healthbridge.example.com',   '407-555-0104', NULL, 'Follow up in two weeks'),
(5, 'Raj Patel',      'CTO',                 'raj@finedge.example.com',            '212-555-0105', NULL, 'Referred by a classmate');
