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


# ============================================
# GREENHOUSE TEST SOURCES
# ============================================

GREENHOUSE_BOARDS = [
    {
        "token": "stripe",
        "company": "Stripe"
    }
]


# ============================================
# FETCH GREENHOUSE JOBS
# ============================================

def fetch_greenhouse_jobs(board):

    token = board["token"]

    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    response = requests.get(
        url,
        params={"content": "true"},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("jobs", [])


# ============================================
# CONVERT JOB
# ============================================

def convert_job(job, board):

    location = ""

    if job.get("location"):
        location = job["location"].get("name", "")

    return {
        "title": job.get("title", ""),
        "company": board["company"],
        "job_url": job.get("absolute_url"),
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
        "is_open": True
    }


# ============================================
# SAVE JOB
# ============================================

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

        # Job already exists.
        # Update the last checked time.

        supabase \
            .table("jobs") \
            .update({
                "last_checked_at": job_data["last_checked_at"],
                "is_open": True
            }) \
            .eq("job_url", job_url) \
            .execute()

        return False

    supabase \
        .table("jobs") \
        .insert(job_data) \
        .execute()

    return True


# ============================================
# MAIN
# ============================================

def main():

    total_found = 0
    total_added = 0

    for board in GREENHOUSE_BOARDS:

        print()
        print("--------------------------------")
        print(
            f"Searching: {board['company']}"
        )
        print("--------------------------------")

        jobs = fetch_greenhouse_jobs(board)

        print(
            f"Greenhouse returned {len(jobs)} jobs."
        )

        total_found += len(jobs)

        for job in jobs:

            job_data = convert_job(
                job,
                board
            )

            if not job_data["job_url"]:
                continue

            try:

                was_added = save_job(job_data)

                if was_added:

                    total_added += 1

                    print(
                        f"Added: {job_data['title']}"
                    )

            except Exception as error:

                print(
                    f"Could not save "
                    f"{job_data['title']}: {error}"
                )

    print()
    print("================================")
    print("JOB RADAR COLLECTION COMPLETE")
    print("================================")
    print(f"Jobs found: {total_found}")
    print(f"Jobs added: {total_added}")


if __name__ == "__main__":
    main()
