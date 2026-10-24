
import requests

GITHUB_API = "https://api.github.com"


def search_developers(skills, limit=10):
    """Find developers through repositories matching required skills."""

    query = " ".join(skills) + " in:readme"

    url = f"{GITHUB_API}/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": limit
    }

    headers = {
        "Accept": "application/vnd.github+json"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        repositories = response.json().get("items", [])

    except requests.RequestException as error:
        print(f"GitHub API error: {error}")
        return

    if not repositories:
        print("No matching repositories found.")
        return

    candidates = {}

    for repo in repositories:
        owner = repo["owner"]["login"]
        username = owner.lower()

        if username not in candidates:
            candidates[username] = {
                "username": owner,
                "profile": repo["owner"]["html_url"],
                "repositories": [],
                "score": 0
            }

        description = repo.get("description") or ""
        language = repo.get("language") or "Not specified"

        relevant_text = (
            repo["name"] + " " +
            description + " " +
            language
        ).lower()

        matches = sum(
            1 for skill in skills
            if skill.lower() in relevant_text
        )

        candidates[username]["score"] += matches * 10
        candidates[username]["repositories"].append({
            "name": repo["name"],
            "url": repo["html_url"],
            "language": language,
            "stars": repo["stargazers_count"],
            "description": description or "No description provided"
        })

    ranked = sorted(
        candidates.values(),
        key=lambda candidate: (
            candidate["score"],
            sum(r["stars"] for r in candidate["repositories"])
        ),
        reverse=True
    )

    print("\n===== GITLINK DEVELOPER MATCHES =====")

    for rank, candidate in enumerate(ranked, start=1):
        print(f"\n{rank}. {candidate['username']}")
        print(f"   Match score: {candidate['score']}")
        print(f"   Profile: {candidate['profile']}")

        for repo in candidate["repositories"]:
            print(f"   Project: {repo['name']}")
            print(f"   Language: {repo['language']}")
            print(f"   Stars: {repo['stars']}")
            print(f"   Link: {repo['url']}")
            print(f"   Description: {repo['description']}")


if __name__ == "__main__":
    print("=== GitLink Developer Discovery ===")
    raw_skills = input(
        "Enter required skills separated by commas: "
    )

    skills = [
        skill.strip()
        for skill in raw_skills.split(",")
        if skill.strip()
    ]

    if skills:
        search_developers(skills)
    else:
        print("Please enter at least one skill.")
