import csv
import html
import re
import requests
from datetime import datetime, timezone

TARGET_ROLES = [
    "site reliability engineer",
    "senior site reliability engineer",
    "lead site reliability engineer",
    "staff site reliability engineer",
    "principal site reliability engineer",
    "sre",
    "cloud engineer",
    "senior cloud engineer",
    "cloud operations engineer",
    "devops engineer",
    "senior devops engineer",
    "platform engineer",
    "senior platform engineer",
    "cloud infrastructure engineer",
    "production support engineer",
]

SKILLS = [
    "aws",
    "azure",
    "gcp",
    "kubernetes",
    "docker",
    "terraform",
    "jenkins",
    "github actions",
    "argocd",
    "gitops",
    "linux",
    "unix",
    "python",
    "shell",
    "bash",
    "grafana",
    "prometheus",
    "splunk",
    "cloudwatch",
    "dynatrace",
    "appdynamics",
    "elk",
    "elasticsearch",
    "kibana",
    "azure monitor",
    "gcp monitoring",
    "incident management",
    "major incident",
    "incident command",
    "production support",
    "root cause analysis",
    "rca",
    "sli",
    "slo",
    "sla",
    "mttr",
    "mttd",
    "postgresql",
    "oracle",
    "mysql",
    "serviceNow",
    "jira",
    "ci/cd",
    "cicd",
    "helm",
    "eks",
    "aks",
    "gke",
    "ecs",
    "ec2",
    "rds",
]


def clean_html(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def calculate_score(job):
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    location = job.get("location", "").lower()

    text = title + " " + description

    score = 0

    # Role match
    for role in TARGET_ROLES:
        if role in title:
            score += 40
            break

    # Skills match
    matched_skills = []

    for skill in SKILLS:
        if skill.lower() in text:
            matched_skills.append(skill)

    score += min(len(matched_skills) * 3, 45)

    # India / remote preference
    if "india" in location:
        score += 10

    if "remote" in location or "remote" in text:
        score += 10

    # Seniority
    senior_words = [
        "senior",
        "sr.",
        "lead",
        "staff",
        "principal",
    ]

    if any(word in title for word in senior_words):
        score += 5

    return score, matched_skills


def get_remotive_jobs():
    jobs = []

    queries = [
        "site reliability engineer",
        "sre",
        "cloud engineer",
        "devops engineer",
        "platform engineer",
        "cloud infrastructure",
        "production support",
    ]

    for query in queries:
        try:
            url = "https://remotive.com/api/remote-jobs"

            response = requests.get(
                url,
                params={"search": query},
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            for item in data.get("jobs", []):
                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": item.get("candidate_required_location", ""),
                    "url": item.get("url", ""),
                    "description": clean_html(
                        item.get("description", "")
                    ),
                    "source": "Remotive",
                    "posted": item.get("publication_date", ""),
                })

        except Exception as error:
            print(f"Remotive error for {query}: {error}")

    return jobs


def get_arbeitnow_jobs():
    jobs = []

    try:
        url = "https://www.arbeitnow.com/api/job-board-api"

        response = requests.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        for item in data.get("data", []):
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "description": clean_html(
                    item.get("description", "")
                ),
                "source": "Arbeitnow",
                "posted": item.get("created_at", ""),
            })

    except Exception as error:
        print(f"Arbeitnow error: {error}")

    return jobs


def deduplicate_jobs(jobs):
    unique = {}

    for job in jobs:
        key = (
            job.get("url")
            or (
                job.get("title", "").lower()
                + "|"
                + job.get("company", "").lower()
            )
        )

        if key:
            unique[key] = job

    return list(unique.values())


def main():
    print("Starting SRE job search...")

    jobs = []

    jobs.extend(get_remotive_jobs())
    jobs.extend(get_arbeitnow_jobs())

    jobs = deduplicate_jobs(jobs)

    results = []

    for job in jobs:
        score, matched_skills = calculate_score(job)

        if score >= 35:
            job["score"] = score
            job["matched_skills"] = ", ".join(matched_skills)
            results.append(job)

    results.sort(
        key=lambda x: x.get("score", 0),
        reverse=True,
    )

    results = results[:50]

    print(f"Found {len(results)} matching jobs.")

    with open(
        "jobs.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        fieldnames = [
            "score",
            "title",
            "company",
            "location",
            "source",
            "posted",
            "matched_skills",
            "url",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for job in results:
            writer.writerow({
                "score": job.get("score", ""),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "source": job.get("source", ""),
                "posted": job.get("posted", ""),
                "matched_skills": job.get("matched_skills", ""),
                "url": job.get("url", ""),
            })

    with open(
        "latest_alert.md",
        "w",
        encoding="utf-8",
    ) as file:

        file.write("# Daily SRE Job Alert\n\n")

        file.write(
            f"Generated: "
            f"{datetime.now(timezone.utc).isoformat()}\n\n"
        )

        if not results:
            file.write("No matching jobs found today.\n")
        else:
            for number, job in enumerate(results, 1):
                file.write(
                    f"## {number}. {job['title']}\n\n"
                )

                file.write(
                    f"**Company:** {job['company']}  \n"
                )

                file.write(
                    f"**Location:** {job['location']}  \n"
                )

                file.write(
                    f"**Match Score:** {job['score']}  \n"
                )

                file.write(
                    f"**Skills:** "
                    f"{job['matched_skills']}  \n"
                )

                file.write(
                    f"**Source:** {job['source']}  \n\n"
                )

                file.write(
                    f"**Apply:** {job['url']}\n\n"
                )

                file.write("---\n\n")


if __name__ == "__main__":
    main()
