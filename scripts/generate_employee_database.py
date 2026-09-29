"""
Realistic Enterprise Employee Database Generator
Creates a comprehensive, high-quality employee dataset for an enterprise AI project.
Utilizes Python, pandas, and Faker.
"""

import os
import random
from datetime import date, timedelta
from typing import Any

from faker import Faker
import pandas as pd

# Initialize Faker with consistent seed
fake = Faker("en_IN")  # Generates realistic Indian enterprise profiles
Faker.seed(42)
random.seed(42)

TOTAL_EMPLOYEES = 500

# 15 Required Enterprise Departments
DEPARTMENTS = [
    "Engineering",
    "Human Resources",
    "Finance",
    "Legal",
    "Marketing",
    "Sales",
    "Operations",
    "IT Support",
    "Customer Service",
    "Data Science",
    "Product Management",
    "Procurement",
    "Administration",
    "Security",
    "Research & Development",
]

# Randomize employee locations across required hubs
LOCATIONS = [
    "Bangalore",
    "Pune",
    "Mumbai",
    "Hyderabad",
    "Chennai",
    "Delhi",
    "Noida",
    "Ahmedabad",
    "Kolkata",
]

# Department-specific designations organized by seniority level
# Levels: Intern (15k-35k), Executive (30k-80k), Senior (80k-150k), Manager (150k-300k)
DESIGNATION_CATALOG = {
    "Engineering": {
        "Intern": ["Software Engineering Intern", "QA Intern"],
        "Executive": ["Software Engineer", "QA Engineer", "DevOps Engineer", "Frontend Developer"],
        "Senior": ["Senior Engineer", "Senior DevOps Engineer", "Tech Lead", "Backend Lead"],
        "Manager": ["Engineering Manager", "Director of Engineering"],
    },
    "Human Resources": {
        "Intern": ["HR Intern", "Recruitment Trainee"],
        "Executive": ["HR Executive", "Talent Acquisition Specialist", "Payroll Executive"],
        "Senior": ["Senior HR Business Partner", "Senior Talent Recruiter", "HR Operations Lead"],
        "Manager": ["HR Manager", "Head of Talent Management"],
    },
    "Finance": {
        "Intern": ["Finance Intern", "Accounts Trainee"],
        "Executive": ["Financial Analyst", "Accounts Executive", "Tax Analyst"],
        "Senior": ["Senior Financial Analyst", "Senior Auditor", "Financial Planning Lead"],
        "Manager": ["Finance Manager", "Treasury Manager"],
    },
    "Legal": {
        "Intern": ["Legal Intern"],
        "Executive": ["Legal Associate", "Compliance Analyst", "Contracts Specialist"],
        "Senior": ["Senior Legal Counsel", "Senior Compliance Specialist"],
        "Manager": ["Legal Manager", "Head of Corporate Governance"],
    },
    "Marketing": {
        "Intern": ["Marketing Intern", "Digital Marketing Trainee"],
        "Executive": ["Marketing Executive", "Content Strategist", "SEO Specialist", "Social Media Executive"],
        "Senior": ["Senior Marketing Strategist", "Brand Lead", "Growth Marketing Lead"],
        "Manager": ["Marketing Manager", "Director of Brand & Growth"],
    },
    "Sales": {
        "Intern": ["Sales Intern", "Business Development Trainee"],
        "Executive": ["Sales Executive", "Business Development Representative", "Inside Sales Associate"],
        "Senior": ["Senior Account Executive", "Regional Sales Lead", "Strategic Enterprise Account Lead"],
        "Manager": ["Sales Manager", "Director of Commercial Sales"],
    },
    "Operations": {
        "Intern": ["Operations Intern"],
        "Executive": ["Operations Executive", "Supply Chain Analyst", "Logistics Coordinator"],
        "Senior": ["Senior Operations Specialist", "Process Improvement Lead", "Supply Chain Lead"],
        "Manager": ["Operations Manager", "Director of Operations"],
    },
    "IT Support": {
        "Intern": ["IT Support Intern", "Helpdesk Trainee"],
        "Executive": ["IT Support Specialist", "System Administrator", "Desktop Support Engineer"],
        "Senior": ["Senior Systems Engineer", "Network Infrastructure Lead", "Cloud Support Lead"],
        "Manager": ["IT Support Manager", "Director of Enterprise IT Infrastructure"],
    },
    "Customer Service": {
        "Intern": ["Customer Service Trainee"],
        "Executive": ["Customer Service Executive", "Customer Support Specialist", "Client Support Associate"],
        "Senior": ["Senior Support Specialist", "Customer Success Lead", "Escalation Specialist"],
        "Manager": ["Customer Service Manager", "Head of Client Relations"],
    },
    "Data Science": {
        "Intern": ["Data Science Intern", "Data Analytics Trainee"],
        "Executive": ["Data Analyst", "BI Developer", "Associate Data Scientist"],
        "Senior": ["Data Scientist", "ML Engineer", "Senior Data Engineer", "AI Research Scientist"],
        "Manager": ["Data Science Manager", "Head of AI & Advanced Analytics"],
    },
    "Product Management": {
        "Intern": ["Product Intern"],
        "Executive": ["Associate Product Manager", "Product Operations Specialist"],
        "Senior": ["Product Manager", "Senior Product Manager", "Product Strategy Lead"],
        "Manager": ["Group Product Manager", "Director of Product Management"],
    },
    "Procurement": {
        "Intern": ["Procurement Intern"],
        "Executive": ["Procurement Executive", "Buyer", "Vendor Relations Associate"],
        "Senior": ["Senior Procurement Specialist", "Sourcing Lead", "Category Specialist"],
        "Manager": ["Procurement Manager", "Head of Strategic Sourcing"],
    },
    "Administration": {
        "Intern": ["Admin Intern"],
        "Executive": ["Administrative Executive", "Facilities Officer", "Office Coordinator"],
        "Senior": ["Senior Admin Coordinator", "Facilities Lead"],
        "Manager": ["Administration Manager", "Director of Corporate Facilities"],
    },
    "Security": {
        "Intern": ["Security Intern", "SOC Trainee"],
        "Executive": ["Security Analyst", "Information Security Officer", "Cybersecurity Associate"],
        "Senior": ["Senior Cybersecurity Analyst", "Threat Hunter", "Cloud Security Lead"],
        "Manager": ["Security Manager", "Head of Cyber Defense"],
    },
    "Research & Development": {
        "Intern": ["R&D Intern", "Research Trainee"],
        "Executive": ["Research Associate", "Lab Specialist", "Innovation Engineer"],
        "Senior": ["Senior Research Scientist", "R&D Lead", "Principal Innovator"],
        "Manager": ["R&D Manager", "Chief Research Director"],
    },
}

# Executive Leadership
C_SUITE = [
    {
        "designation": "Chief Executive Officer (CEO)",
        "department": "Administration",
        "manager": "Board of Directors",
        "salary_range": (400000, 500000),
        "bonus_range": (150000, 250000),
        "level": "C-Suite",
    },
    {
        "designation": "Chief Technology Officer (CTO)",
        "department": "Engineering",
        "manager": "CEO",
        "salary_range": (350000, 450000),
        "bonus_range": (120000, 200000),
        "level": "C-Suite",
    },
    {
        "designation": "Chief Financial Officer (CFO)",
        "department": "Finance",
        "manager": "CEO",
        "salary_range": (350000, 450000),
        "bonus_range": (120000, 200000),
        "level": "C-Suite",
    },
    {
        "designation": "Chief Human Resources Officer (CHRO)",
        "department": "Human Resources",
        "manager": "CEO",
        "salary_range": (320000, 420000),
        "bonus_range": (100000, 180000),
        "level": "C-Suite",
    },
]


def random_date(start_year: int = 2018, end_year: int = 2026) -> str:
    """Generate realistic joining dates from 2018 to 2026."""
    start_date = date(start_year, 1, 1)
    end_date = min(date(end_year, 9, 28), date.today())
    days_range = (end_date - start_date).days
    random_days = random.randint(0, max(0, days_range))
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")


def compute_salary_and_bonus(level: str, emp_type: str) -> tuple[float, float, float]:
    """Calculate salary, bonus, and annual_ctc based on strict enterprise salary rules.

    Salary rules:
    - Intern: 15,000 - 35,000
    - Executive: 30,000 - 80,000
    - Senior: 80,000 - 150,000
    - Manager: 150,000 - 300,000
    - annual_ctc = salary * 12 + bonus
    """
    if emp_type == "Intern" or level == "Intern":
        salary = round(random.uniform(15000, 35000), -2)
        bonus = round(random.uniform(1000, 5000), -2)
    elif level == "Executive":
        salary = round(random.uniform(30000, 80000), -2)
        bonus = round(random.uniform(5000, 20000), -2)
    elif level == "Senior":
        salary = round(random.uniform(80000, 150000), -2)
        bonus = round(random.uniform(15000, 40000), -2)
    elif level == "Manager":
        salary = round(random.uniform(150000, 300000), -2)
        bonus = round(random.uniform(30000, 80000), -2)
    else:  # C-Suite / Executive
        salary = round(random.uniform(350000, 500000), -2)
        bonus = round(random.uniform(100000, 250000), -2)

    annual_ctc = round((salary * 12) + bonus, 2)
    return float(salary), float(bonus), float(annual_ctc)


def generate_employee_database(total_count: int = TOTAL_EMPLOYEES) -> pd.DataFrame:
    """Generate a realistic, normalized enterprise employee database."""
    used_emails: set[str] = set()
    records: list[dict[str, Any]] = []

    # Map to track department managers for building realistic hierarchy
    dept_managers: dict[str, list[str]] = {dept: [] for dept in DEPARTMENTS}

    # Step 1: Create Executive Leadership first so they can manage departments
    ceo_name = ""
    for idx, exec_info in enumerate(C_SUITE, start=1):
        emp_id = f"EMP{idx:04d}"
        gender = random.choice(["Male", "Female"])
        first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"

        if "CEO" in exec_info["designation"]:
            ceo_name = full_name
            mgr = "Board of Directors"
        else:
            mgr = ceo_name or "Board of Directors"

        # Unique company email
        email = f"{first_name.lower()}.{last_name.lower()}@enterprise.com"
        used_emails.add(email)

        salary = round(random.uniform(*exec_info["salary_range"]), -2)
        bonus = round(random.uniform(*exec_info["bonus_range"]), -2)
        annual_ctc = round(salary * 12 + bonus, 2)

        record = {
            "employee_id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "phone": fake.phone_number()[:14],
            "department": exec_info["department"],
            "designation": exec_info["designation"],
            "manager_name": mgr,
            "location": random.choice(LOCATIONS),
            "date_of_joining": random_date(2018, 2021),  # Leadership joined earlier
            "employment_type": "Full-Time",
            "salary": float(salary),
            "bonus": float(bonus),
            "annual_ctc": float(annual_ctc),
            "performance_rating": round(random.uniform(4.2, 5.0), 1),
            "gender": gender,
            "age": random.randint(45, 62),
        }
        records.append(record)
        dept_managers[exec_info["department"]].append(full_name)

    # Step 2: Pre-seed at least 1 Manager per department to anchor hierarchy
    curr_id = len(records) + 1
    for dept in DEPARTMENTS:
        # Check if dept already has a manager from C-suite
        if not dept_managers[dept]:
            emp_id = f"EMP{curr_id:04d}"
            curr_id += 1
            gender = random.choice(["Male", "Female"])
            first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
            last_name = fake.last_name()
            full_name = f"{first_name} {last_name}"

            email = f"{first_name.lower()}.{last_name.lower()}@enterprise.com"
            ctr = 1
            while email in used_emails:
                email = f"{first_name.lower()}.{last_name.lower()}{ctr}@enterprise.com"
                ctr += 1
            used_emails.add(email)

            manager_title = DESIGNATION_CATALOG[dept]["Manager"][0]
            salary, bonus, ctc = compute_salary_and_bonus("Manager", "Full-Time")

            records.append({
                "employee_id": emp_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "email": email,
                "phone": fake.phone_number()[:14],
                "department": dept,
                "designation": manager_title,
                "manager_name": ceo_name,
                "location": random.choice(LOCATIONS),
                "date_of_joining": random_date(2018, 2022),
                "employment_type": "Full-Time",
                "salary": salary,
                "bonus": bonus,
                "annual_ctc": ctc,
                "performance_rating": round(random.uniform(3.5, 4.8), 1),
                "gender": gender,
                "age": random.randint(34, 52),
            })
            dept_managers[dept].append(full_name)

    # Step 3: Generate remaining workforce across Senior, Executive, and Intern
    levels = ["Senior", "Executive", "Intern"]
    level_weights = [0.35, 0.50, 0.15]  # Realistic workforce pyramid

    while len(records) < total_count:
        emp_id = f"EMP{len(records) + 1:04d}"
        gender = random.choice(["Male", "Female"])
        first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"

        # Generate unique email
        base_email = f"{first_name.lower()}.{last_name.lower()}@enterprise.com"
        email = base_email
        c = 1
        while email in used_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{c}@enterprise.com"
            c += 1
        used_emails.add(email)

        department = random.choice(DEPARTMENTS)
        level = random.choices(levels, weights=level_weights, k=1)[0]
        designations_for_level = DESIGNATION_CATALOG[department][level]
        designation = random.choice(designations_for_level)

        # Employment type
        if level == "Intern":
            emp_type = "Intern"
            age = random.randint(20, 24)
        else:
            emp_type = random.choices(["Full-Time", "Contract"], weights=[0.88, 0.12], k=1)[0]
            age = random.randint(28, 44) if level == "Senior" else random.randint(22, 32)

        # Compute salary rules
        salary, bonus, ctc = compute_salary_and_bonus(level, emp_type)

        # Realistic manager assignment from department's management pool
        mgr_candidates = dept_managers.get(department) or [ceo_name]
        manager_name = random.choice(mgr_candidates)

        records.append({
            "employee_id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": email,
            "phone": fake.phone_number()[:14],
            "department": department,
            "designation": designation,
            "manager_name": manager_name,
            "location": random.choice(LOCATIONS),
            "date_of_joining": random_date(2018, 2026),
            "employment_type": emp_type,
            "salary": salary,
            "bonus": bonus,
            "annual_ctc": ctc,
            "performance_rating": round(random.choices([3.0, 3.5, 4.0, 4.5, 5.0], weights=[0.15, 0.30, 0.35, 0.15, 0.05], k=1)[0], 1),
            "gender": gender,
            "age": age,
        })

    df = pd.DataFrame(records)
    return df


def main():
    print("=" * 80)
    print("ENTERPRISE EMPLOYEE DATABASE GENERATOR (500+ EMPLOYEES)")
    print("=" * 80)

    df = generate_employee_database(total_count=TOTAL_EMPLOYEES)

    # Output file paths
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "enterprise_employees.csv")
    df.to_csv(csv_path, index=False)

    print(f"\n[SUCCESS] Generated {len(df)} employee records successfully.")
    print(f"[SAVED] Dataset saved to: {csv_path}\n")

    # 1. Display first 10 records
    print("-" * 80)
    print("1. FIRST 10 GENERATED EMPLOYEE RECORDS:")
    print("-" * 80)
    display_cols = ["employee_id", "full_name", "department", "designation", "manager_name", "salary", "annual_ctc", "location"]
    print(df[display_cols].head(10).to_string(index=False))

    # 2. Print department-wise employee counts
    print("\n" + "-" * 80)
    print("2. DEPARTMENT-WISE EMPLOYEE COUNTS:")
    print("-" * 80)
    dept_counts = df["department"].value_counts().reset_index()
    dept_counts.columns = ["Department", "Employee Count"]
    print(dept_counts.to_string(index=False))

    # 3. Print average salary by department
    print("\n" + "-" * 80)
    print("3. AVERAGE SALARY AND CTC BY DEPARTMENT:")
    print("-" * 80)
    dept_salaries = (
        df.groupby("department")
        .agg(
            Avg_Monthly_Salary=("salary", "mean"),
            Avg_Annual_CTC=("annual_ctc", "mean"),
            Total_Employees=("employee_id", "count"),
        )
        .reset_index()
    )
    dept_salaries["Avg_Monthly_Salary"] = dept_salaries["Avg_Monthly_Salary"].apply(lambda x: f"${x:,.2f}")
    dept_salaries["Avg_Annual_CTC"] = dept_salaries["Avg_Annual_CTC"].apply(lambda x: f"${x:,.2f}")
    print(dept_salaries.to_string(index=False))

    print("\n" + "=" * 80)
    print("DATABASE GENERATION AND SUMMARY COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
