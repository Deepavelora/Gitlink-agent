import requests

def search_opportunities(keywords, limit=5):
    sources = [
        ("Arbeitnow", "https://www.arbeitnow.com/api/job-board-api", "data"),
        ("Remotive", "https://remotive.com/api/remote-jobs", "jobs"),
    ]
    results = []
    terms = [x.lower() for x in keywords if x.strip()]

    for name, url, key in sources:
        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            for job in response.json().get(key, []):
                title = job.get("title", "")
                company = job.get("company_name", "Not listed")
                description = job.get("description", "")
                link = job.get("url", "")
                location = job.get("location", job.get("candidate_required_location", "Not listed"))
                text = f"{title} {company} {description}".lower()
                matched = [term for term in terms if term in text]
                if matched and link:
                    results.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "source": name,
                        "url": link,
                        "matched_terms": matched,
                    })
        except (requests.RequestException, ValueError) as error:
            print(f"{name} source unavailable: {error}")

    results.sort(key=lambda item: len(item["matched_terms"]), reverse=True)
    unique = []
    seen = set()
    for job in results:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique.append(job)
        if len(unique) >= limit:
            break
    return unique


if __name__ == "__main__":
    query = input("Enter keywords (e.g. python internship): ")
    for i, job in enumerate(search_opportunities(query.split()), 1):
        print(f"\n{i}. {job['title']} — {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Source: {job['source']}")
        print(f"Matched: {', '.join(job['matched_terms'])}")
        print(f"Link: {job['url']}")
