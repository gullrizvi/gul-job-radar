import os
import requests
from datetime import datetime, timezone
from supabase import create_client


# ============================================
# GUL JOB RADAR - JOB COLLECTOR
# ============================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY environment variables are required."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# --------------------------------------------
# Greenhouse companies to search
# --------------------------------------------

GREENHOUSE_BOARDS = [
    "acled",
]


# --------------------------------------------
# Fetch jobs from one Greenhouse board
# --------------------------------------------

def fetch_greenhouse_jobs(board_token):

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    response = requests.get(
        url,
        params={"content": "true"},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("jobs", [])


# --------------------------------------------
# Convert Greenhouse job into our database format
# --------------------------------------------

def convert_job(job, board_token):

    location = ""

    if job.get("location"):
        location = job["location"].get("name", "")

    job_url = job.get("absolute_url")

    return {
        "title": job.get("title", ""),
        "company": board_token,
        "job_url": job_url,
        "location": location,
        "remote_status": "Unknown",
        "employment_type": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": None,
        "description": job.get("content", ""),
        "experience_required": None,
        "application_deadline": None,
        "source": "Greenhouse",
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "is_open": True,
    }


# --------------------------------------------
# Save jobs to Supabase
# --------------------------------------------

def save_job(job_data):

    job_url = job_data["job_url"]

    existing = (
        supabase
        .table("jobs")
        .select("id")
        .eq("job_url", job_url)
        .execute()
    )

    if existing.data:
        print(f"Already exists: {job_data['title']}")
        return

    supabase.table("jobs").insert(job_data).execute()

    print(f"Added: {job_data['title']}")


# --------------------------------------------
# Main collector
# --------------------------------------------

def main():

    total_found = 0
    total_added = 0

    for board in GREENHOUSE_BOARDS:

        print(f"\nSearching Greenhouse board: {board}")

        try:

            jobs = fetch_greenhouse_jobs(board)

            print(f"Found {len(jobs)} jobs.")

            total_found += len(jobs)

            for job in jobs:

                job_data = convert_job(job, board)

                try:

                    before = (
                        supabase
                        .table("jobs")
                        .select("id")
                        .eq("job_url", job_data["job_url"])
                        .execute()
                    )

                    if not before.data:

                        save_job(job_data)
                        total_added += 1

                except Exception as error:

                    print(
                        f"Could not save job "
                        f"{job_data.get('title', '')}: {error}"
                    )

        except Exception as error:

            print(
                f"Could not read Greenhouse board "
                f"{board}: {error}"
            )

    print("\n================================")
    print("JOB RADAR COLLECTION COMPLETE")
    print("================================")
    print(f"Jobs found: {total_found}")
    print(f"Jobs added: {total_added}")


if __name__ == "__main__":
    main()
