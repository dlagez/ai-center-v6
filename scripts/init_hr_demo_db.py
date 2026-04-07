import argparse
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.sql.db import ensure_db_file
from src.config.settings import settings


DEPARTMENTS = [
    (1, "Human Resources", "Li Na", 4200000.0),
    (2, "Engineering", "Wang Lei", 18500000.0),
    (3, "Sales", "Zhao Min", 9600000.0),
    (4, "Finance", "Chen Yu", 5100000.0),
]

EMPLOYEES = [
    (1001, "Alice Zhang", "alice.zhang@demo.com", "HRBP", 1, "2022-03-14", "active", "Shanghai", 23000.0),
    (1002, "Bob Chen", "bob.chen@demo.com", "Recruiter", 1, "2023-07-03", "active", "Shanghai", 18000.0),
    (1003, "Cathy Liu", "cathy.liu@demo.com", "Backend Engineer", 2, "2021-11-08", "active", "Beijing", 32000.0),
    (1004, "David Wu", "david.wu@demo.com", "Frontend Engineer", 2, "2024-01-15", "active", "Hangzhou", 28000.0),
    (1005, "Emma Sun", "emma.sun@demo.com", "Sales Manager", 3, "2020-05-20", "active", "Shenzhen", 35000.0),
    (1006, "Frank Guo", "frank.guo@demo.com", "Account Executive", 3, "2023-09-11", "active", "Guangzhou", 22000.0),
    (1007, "Grace He", "grace.he@demo.com", "Financial Analyst", 4, "2022-12-01", "active", "Shanghai", 26000.0),
    (1008, "Henry Xu", "henry.xu@demo.com", "Data Engineer", 2, "2021-06-18", "on_leave", "Beijing", 34000.0),
]

JOBS = [
    (2001, "Senior Recruiter", 1, "open", "2026-02-10", 1),
    (2002, "AI Engineer", 2, "open", "2026-03-01", 2),
    (2003, "Solutions Consultant", 3, "closed", "2026-01-12", 1),
    (2004, "Payroll Specialist", 4, "open", "2026-03-15", 1),
]

CANDIDATES = [
    (3001, "Ivy Gao", 2001, "onsite", "2026-03-05", "Li Na"),
    (3002, "Jason Qian", 2002, "offer", "2026-03-18", "Wang Lei"),
    (3003, "Kelly Fan", 2002, "screening", "2026-04-01", "Wang Lei"),
    (3004, "Leo Tang", 2004, "interview", "2026-03-28", "Chen Yu"),
    (3005, "Mia Zhou", 2003, "hired", "2026-02-22", "Zhao Min"),
]

ATTENDANCE = [
    (4001, 1001, "2026-04-01", "present", 0.0),
    (4002, 1002, "2026-04-01", "present", 1.5),
    (4003, 1003, "2026-04-01", "present", 2.0),
    (4004, 1004, "2026-04-01", "remote", 0.0),
    (4005, 1005, "2026-04-01", "present", 0.5),
    (4006, 1006, "2026-04-01", "absent", 0.0),
    (4007, 1007, "2026-04-01", "present", 0.0),
    (4008, 1008, "2026-04-01", "leave", 0.0),
]

PERFORMANCE_REVIEWS = [
    (5001, 1001, "2025-H2", 4.3, "Strong stakeholder management"),
    (5002, 1002, "2025-H2", 3.9, "Solid pipeline delivery"),
    (5003, 1003, "2025-H2", 4.7, "Critical backend contributor"),
    (5004, 1004, "2025-H2", 4.1, "Fast ramp-up in new team"),
    (5005, 1005, "2025-H2", 4.8, "Exceeded sales targets"),
    (5006, 1006, "2025-H2", 3.6, "Needs stronger forecasting"),
    (5007, 1007, "2025-H2", 4.2, "Consistent reporting quality"),
    (5008, 1008, "2025-H2", 4.5, "Strong data platform ownership"),
]

PAYROLL = [
    (6001, 1001, "2026-03", 23000.0, 1500.0, 4200.0, 20300.0),
    (6002, 1002, "2026-03", 18000.0, 1200.0, 3300.0, 15900.0),
    (6003, 1003, "2026-03", 32000.0, 5000.0, 5900.0, 31100.0),
    (6004, 1004, "2026-03", 28000.0, 3200.0, 5100.0, 26100.0),
    (6005, 1005, "2026-03", 35000.0, 12000.0, 6800.0, 40200.0),
    (6006, 1006, "2026-03", 22000.0, 4500.0, 4100.0, 22400.0),
    (6007, 1007, "2026-03", 26000.0, 1800.0, 4700.0, 23100.0),
    (6008, 1008, "2026-03", 34000.0, 6000.0, 6200.0, 33800.0),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a demo HR SQLite database.")
    parser.add_argument(
        "--db-path",
        default=settings.sql_agent_default_db_path or "D:/data/demo.db",
        help="SQLite database file path.",
    )
    args = parser.parse_args()

    db_path = ensure_db_file(args.db_path)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS payroll;
            DROP TABLE IF EXISTS performance_reviews;
            DROP TABLE IF EXISTS attendance;
            DROP TABLE IF EXISTS candidates;
            DROP TABLE IF EXISTS jobs;
            DROP TABLE IF EXISTS employees;
            DROP TABLE IF EXISTS departments;

            CREATE TABLE departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL,
                director_name TEXT NOT NULL,
                annual_budget REAL NOT NULL
            );

            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                title TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                hire_date TEXT NOT NULL,
                employment_status TEXT NOT NULL,
                city TEXT NOT NULL,
                base_salary REAL NOT NULL,
                FOREIGN KEY (department_id) REFERENCES departments(department_id)
            );

            CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                job_title TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                job_status TEXT NOT NULL,
                opened_date TEXT NOT NULL,
                headcount INTEGER NOT NULL,
                FOREIGN KEY (department_id) REFERENCES departments(department_id)
            );

            CREATE TABLE candidates (
                candidate_id INTEGER PRIMARY KEY,
                candidate_name TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                stage TEXT NOT NULL,
                applied_date TEXT NOT NULL,
                recruiter_name TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );

            CREATE TABLE attendance (
                attendance_id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL,
                overtime_hours REAL NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            );

            CREATE TABLE performance_reviews (
                review_id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                review_cycle TEXT NOT NULL,
                rating REAL NOT NULL,
                summary TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            );

            CREATE TABLE payroll (
                payroll_id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                payroll_month TEXT NOT NULL,
                base_pay REAL NOT NULL,
                bonus REAL NOT NULL,
                deductions REAL NOT NULL,
                net_pay REAL NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            );
            """
        )

        conn.executemany(
            "INSERT INTO departments(department_id, department_name, director_name, annual_budget) VALUES (?, ?, ?, ?)",
            DEPARTMENTS,
        )
        conn.executemany(
            """
            INSERT INTO employees(
                employee_id, full_name, email, title, department_id, hire_date,
                employment_status, city, base_salary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            EMPLOYEES,
        )
        conn.executemany(
            "INSERT INTO jobs(job_id, job_title, department_id, job_status, opened_date, headcount) VALUES (?, ?, ?, ?, ?, ?)",
            JOBS,
        )
        conn.executemany(
            "INSERT INTO candidates(candidate_id, candidate_name, job_id, stage, applied_date, recruiter_name) VALUES (?, ?, ?, ?, ?, ?)",
            CANDIDATES,
        )
        conn.executemany(
            "INSERT INTO attendance(attendance_id, employee_id, attendance_date, status, overtime_hours) VALUES (?, ?, ?, ?, ?)",
            ATTENDANCE,
        )
        conn.executemany(
            "INSERT INTO performance_reviews(review_id, employee_id, review_cycle, rating, summary) VALUES (?, ?, ?, ?, ?)",
            PERFORMANCE_REVIEWS,
        )
        conn.executemany(
            """
            INSERT INTO payroll(
                payroll_id, employee_id, payroll_month, base_pay, bonus, deductions, net_pay
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            PAYROLL,
        )
        conn.commit()

    print(f"Initialized HR demo database: {db_path}")
    print("Tables: departments, employees, jobs, candidates, attendance, performance_reviews, payroll")


if __name__ == "__main__":
    main()
