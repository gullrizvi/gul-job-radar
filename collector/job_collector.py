import os
import requests
from bs4 import BeautifulSoup
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

HEADERS = {
    "User-Agent": "Gul Job Radar/1.0"
}


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
# SAVE THE CHILDREN
# ============================================

SAVE_THE_CHILDREN_URL = (
    "https://www.savethechildren.net/careers/apply"
)


# ============================================
# FETCH GREENHOUSE JOBS
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


# ============================================
# CONVERT GREENHOUSE JOB
# ============================================

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
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "is_open": True
    }


# ============================================
# FETCH SAVE THE CHILDREN JOBS
# ============================================

def fetch_save_the_children_jobs():

    jobs = []
    seen_urls = set()

    # The public careers page uses pagination.
    # We check the first several pages so we do
    # not only collect the jobs visible on page 1.

    for page in range(0, 10):

        if page == 0:
            url = SAVE_THE_CHILDREN_URL
        else:
            url = f"{SAVE_THE_CHILDREN_URL}?page={page}"

        print()
        print("--------------------------------")
        print(
            f"Save the Children page: {page}"
        )
        print("--------------------------------")

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        detail_links = soup.select(
            'a[href*="/careers/apply/details?jid="]'
        )

        if not detail_links:
            print("No more Save the Children jobs found.")
            break

        page_new_jobs = 0

        for link in detail_links:

            href = link.get("href")

            if not href:
                continue

            if href.startswith("/"):
                job_url = (
                    "https://www.savethechildren.net"
                    + href
                )
            else:
                job_url = href

            if job_url in seen_urls:
                continue

            seen_urls.add(job_url)

            title = link.get_text(
                " ",
                strip=True
            )

            if not title:
                title = "Save the Children vacancy"

            # Fetch the individual job page
            # so we can store its description.

            try:

                detail_response = requests.get(
                    job_url,
                    headers=HEADERS,
                    timeout=30
                )

                detail_response.raise_for_status()

                detail_soup = BeautifulSoup(
                    detail_response.text,
                    "html.parser"
                )

                description = detail_soup.get_text(
                    " ",
                    strip=True
                )

            except Exception as error:

                print(
                    f"Could not read job details: "
                    f"{error}"
                )

                description = ""

            # Worldwide roles are potentially relevant
            # to Pakistan, but we will NOT assume every
            # Worldwide role is automatically eligible.
            # Later matching logic will verify this.

            remote_status = "Unknown"

            if "Worldwide" in description:
                remote_status = "Worldwide"

            job_data = {
                "title": title,
                "company": "Save the Children International",
                "job_url": job_url,
                "location": "Worldwide"
                    if "Worldwide" in description
                    else "",
                "remote_status": remote_status,
                "employment_type": None,
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "salary_period": None,
                "description": description,
                "experience_required": None,
                "application_deadline": None,
                "source": "Save the Children International",
                "last_checked_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "is_open": True
            }

            jobs.append(job_data)
            page_new_jobs += 1

        print(
            f"Found {page_new_jobs} new jobs."
        )

    return jobs


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

        supabase \
            .table("jobs") \
            .update({
                "last_checked_at":
                    job_data["last_checked_at"],
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

    # ------------------------------------------
    # GREENHOUSE
    # ------------------------------------------

    for board in GREENHOUSE_BOARDS:

        print()
        print("================================")
        print(
            f"Searching: {board['company']}"
        )
        print("================================")

        jobs = fetch_greenhouse_jobs(board)

        print(
            f"Greenhouse returned {len(jobs)} jobs."
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

    # ------------------------------------------
    # SAVE THE CHILDREN
    # ------------------------------------------

    print()
    print("================================")
    print("Searching: Save the Children")
    print("================================")

    try:

        save_the_children_jobs = (
            fetch_save_the_children_jobs()
        )

        print(
            "Save the Children returned "
            f"{len(save_the_children_jobs)} jobs."
        )

        total_found += len(
            save_the_children_jobs
        )

        for job_data in save_the_children_jobs:

            try:

                was_added = save_job(job_data)

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
            "Could not read Save the Children: "
            f"{error}"
        )

    # ------------------------------------------
    # COMPLETE
    # ------------------------------------------

    print()
    print("================================")
    print("JOB RADAR COLLECTION COMPLETE")
    print("================================")
    print(f"Jobs found: {total_found}")
    print(f"Jobs added: {total_added}")


if __name__ == "__main__":
    main()
