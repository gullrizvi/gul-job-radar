import os
import requests
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY environment variables are required."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================
# GREENHOUSE SOURCES
# ============================================

GREENHOUSE_BOARDS = [
    {
        "token": "stripe",
        "company": "Stripe"
    }
]


# ============================================
# WORLD BANK GROUP
# ============================================

WORLD_BANK_BASE_URL = (
    "https://worldbankgroup.csod.com"
)

WORLD_BANK_CAREER_URL = (
    "https://worldbankgroup.csod.com/"
    "ux/ats/careersite/1/home?c=worldbankgroup"
)


# ============================================
# GREENHOUSE FUNCTIONS
# ============================================

def fetch_greenhouse_jobs(board):
    token = board["token"]

    url = (
        f"https://boards-api.greenhouse.io/"
        f"v1/boards/{token}/jobs"
    )

    response = requests.get(
        url,
        params={"content": "true"},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("jobs", [])


def convert_greenhouse_job(job, board):
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
        "last_checked_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "is_open": True
    }


# ============================================
# WORLD BANK FUNCTIONS
# ============================================

def fetch_world_bank_jobs():
    print()
    print("--------------------------------")
    print("Searching: World Bank Group")
    print("--------------------------------")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*"
    }

    response = requests.get(
        WORLD_BANK_CAREER_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    print(
        f"World Bank careers page loaded: "
        f"{response.status_code}"
    )

    return []


# ============================================
# DATABASE FUNCTIONS
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
        (
            supabase
            .table("jobs")
            .update({
                "last_checked_at": job_data[
                    "last_checked_at"
                ],
                "is_open": True
            })
            .eq("job_url", job_url)
            .execute()
        )

        return False

    (
        supabase
        .table("jobs")
        .insert(job_data)
        .execute()
    )

    return True


# ============================================
# MAIN COLLECTOR
# ============================================

def main():

    total_found = 0
    total_added = 0

    # ----------------------------------------
    # GREENHOUSE
    # ----------------------------------------

    for board in GREENHOUSE_BOARDS:

        print()
        print("--------------------------------")
        print(f"Searching: {board['company']}")
        print("--------------------------------")

        try:
            jobs = fetch_greenhouse_jobs(board)

            print(
                f"Greenhouse returned "
                f"{len(jobs)} jobs."
            )

            total_found += len(jobs)

            for job in jobs:

                job_data = convert_greenhouse_job(
                    job,
                    board
                )

                if not job_data["job_url"]:
                    continue

                try:

                    was_added = save_job(
                        job_data
                    )

                    if was_added:

                        total_added += 1

                        print(
                            f"Added: "
                            f"{job_data['title']}"
                        )

                except Exception as error:

                    print(
                        f"Could not save "
                        f"{job_data['title']}: "
                        f"{error}"
                    )

        except Exception as error:

            print(
                f"Could not read "
                f"{board['company']}: "
                f"{error}"
            )


    # ----------------------------------------
    # WORLD BANK GROUP
    # ----------------------------------------

    try:

        world_bank_jobs = (
            fetch_world_bank_jobs()
        )

        print(
            f"World Bank returned "
            f"{len(world_bank_jobs)} jobs."
        )

        total_found += len(
            world_bank_jobs
        )

    except Exception as error:

        print(
            f"Could not read World Bank Group: "
            f"{error}"
        )


    # ----------------------------------------
    # COMPLETE
    # ----------------------------------------

    print()
    print("================================")
    print("JOB RADAR COLLECTION COMPLETE")
    print("================================")
    print(
        f"Jobs found: {total_found}"
    )
    print(
        f"Jobs added: {total_added}"
    )


if __name__ == "__main__":
    main()
