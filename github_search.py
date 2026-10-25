import html
import re
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GITHUB_API = "https://api.github.com"

# High-quality fallback developer profiles if GitHub rate-limits unauthenticated calls
CURATED_DEVELOPERS = [
    {
        "id": "dev_fetchai",
        "username": "fetchai",
        "profile_url": "https://github.com/fetchai",
        "avatar_url": "https://avatars.githubusercontent.com/u/35212519?v=4",
        "top_repo": "uAgents",
        "top_repo_url": "https://github.com/fetchai/uAgents",
        "description": "Fast and lightweight framework for creating decentralized autonomous AI agents in Python.",
        "language": "Python",
        "stars": 4200,
        "matched_skills": ["python", "ai", "agents", "decentralized"],
        "score": 98,
    },
    {
        "id": "dev_tiangolo",
        "username": "tiangolo",
        "profile_url": "https://github.com/tiangolo",
        "avatar_url": "https://avatars.githubusercontent.com/u/1326112?v=4",
        "top_repo": "fastapi",
        "top_repo_url": "https://github.com/tiangolo/fastapi",
        "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
        "language": "Python",
        "stars": 78000,
        "matched_skills": ["python", "fastapi", "asyncio", "rest"],
        "score": 96,
    },
    {
        "id": "dev_langchain-ai",
        "username": "langchain-ai",
        "profile_url": "https://github.com/langchain-ai",
        "avatar_url": "https://avatars.githubusercontent.com/u/126733545?v=4",
        "top_repo": "langchain",
        "top_repo_url": "https://github.com/langchain-ai/langchain",
        "description": "Building context-aware reasoning applications and autonomous agent pipelines.",
        "language": "Python",
        "stars": 98000,
        "matched_skills": ["python", "ai", "llm", "orchestration"],
        "score": 94,
    },
    {
        "id": "dev_astral-sh",
        "username": "astral-sh",
        "profile_url": "https://github.com/astral-sh",
        "avatar_url": "https://avatars.githubusercontent.com/u/115962839?v=4",
        "top_repo": "uv",
        "top_repo_url": "https://github.com/astral-sh/uv",
        "description": "An extremely fast Python package and project manager written in Rust.",
        "language": "Rust",
        "stars": 44000,
        "matched_skills": ["rust", "python", "performance", "tooling"],
        "score": 92,
    },
]


def clean_text(raw_text: str) -> str:
    """Unescape and sanitize text."""
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove non-ascii emojis or encode safely so console and json don't fail
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.split())[:250]


def search_developers(skills, limit=5):
    """
    Find open-source developers and projects through repositories matching required skills.
    Returns structured list of candidate dictionaries.
    """
    skill_terms = [s.strip().lower() for s in skills if s.strip()]
    if not skill_terms:
        skill_terms = ["python", "agent"]

    query = " ".join(skill_terms) + " in:readme,description"
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit * 3, 30),
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GitLink-Agent/1.0 (https://github.com/Deepavelora/Gitlink-agent)",
    }

    repositories = []
    try:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.exceptions.SSLError:
            response = requests.get(url, params=params, headers=headers, verify=False, timeout=10)

        if response.status_code == 200:
            repositories = response.json().get("items", [])
    except Exception as error:
        # Request failed or timeout
        pass

    candidates = {}

    for repo in repositories:
        owner = repo["owner"]["login"]
        username = owner.lower()

        if username not in candidates:
            candidates[username] = {
                "id": f"dev_{username}",
                "username": owner,
                "profile_url": repo["owner"].get("html_url", f"https://github.com/{owner}"),
                "avatar_url": repo["owner"].get("avatar_url", f"https://github.com/{owner}.png"),
                "repositories": [],
                "score": 0,
            }

        desc = repo.get("description") or ""
        lang = repo.get("language") or "Python"
        clean_desc = clean_text(desc)

        relevant_text = f"{repo['name']} {clean_desc} {lang}".lower()
        matched = [s for s in skill_terms if s in relevant_text]

        candidates[username]["score"] += (len(matched) * 15) + min(repo.get("stargazers_count", 0) // 100, 30)
        candidates[username]["repositories"].append({
            "name": repo["name"],
            "url": repo["html_url"],
            "language": lang,
            "stars": repo.get("stargazers_count", 0),
            "description": clean_desc or "Open source project repository",
            "matched": matched,
        })

    results = []
    for cand in candidates.values():
        repos = sorted(cand["repositories"], key=lambda r: r["stars"], reverse=True)
        top = repos[0]
        # Aggregate matched skills
        all_matched = list({m for r in repos for m in r.get("matched", [])})
        if not all_matched:
            all_matched = skill_terms[:2]

        results.append({
            "id": cand["id"],
            "username": cand["username"],
            "profile_url": cand["profile_url"],
            "avatar_url": cand["avatar_url"],
            "top_repo": top["name"],
            "top_repo_url": top["url"],
            "description": top["description"],
            "language": top["language"],
            "stars": sum(r["stars"] for r in repos),
            "matched_skills": all_matched,
            "score": min(cand["score"], 99),
        })

    # Fallback to curated developers if API returned fewer results
    if len(results) < limit:
        for cur in CURATED_DEVELOPERS:
            text = f"{cur['username']} {cur['top_repo']} {cur['description']} {' '.join(cur['matched_skills'])}".lower()
            matched = [s for s in skill_terms if s in text]
            if not skill_terms or matched or len(results) == 0:
                cur_copy = dict(cur)
                cur_copy["matched_skills"] = matched if matched else cur["matched_skills"][:2]
                results.append(cur_copy)

    # Sort candidates by match score and stars
    results.sort(key=lambda c: (c["score"], c["stars"]), reverse=True)

    # Deduplicate
    unique = []
    seen = set()
    for c in results:
        if c["username"] not in seen:
            seen.add(c["username"])
            unique.append(c)
        if len(unique) >= limit:
            break

    return unique


if __name__ == "__main__":
    skills = ["python", "fastapi"]
    print(f"Searching GitHub developers for: {skills}")
    devs = search_developers(skills, limit=3)
    for i, dev in enumerate(devs, 1):
        print(f"\n{i}. [{dev['id']}] {dev['username']} (Score: {dev['score']}%)")
        print(f"   Top Repo: {dev['top_repo']} ({dev['stars']} stars, {dev['language']})")
        print(f"   URL: {dev['profile_url']}")
        print(f"   Desc: {dev['description']}")
