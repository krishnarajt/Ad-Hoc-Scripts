import requests
import time

GITHUB_USERNAME = "krishanrajt"
GITHUB_TOKEN = "YOUR_TOKEN"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_all_repos():
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/user/repos?per_page=100&page={page}"
        res = requests.get(url, headers=HEADERS)

        if res.status_code != 200:
            raise Exception(f"Failed to fetch repos: {res.text}")

        data = res.json()
        if not data:
            break

        repos.extend(data)
        page += 1

    return repos


def get_contributors(owner, repo):
    contributors = set()
    page = 1

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100&page={page}"
        res = requests.get(url, headers=HEADERS)

        if res.status_code == 204:
            break  # no contributors

        if res.status_code != 200:
            print(f"Skipping {repo}: {res.status_code}")
            break

        data = res.json()
        if not data:
            break

        for user in data:
            contributors.add(user["login"])

        page += 1

    return contributors


def main():
    all_contributors = set()

    repos = get_all_repos()
    print(f"Found {len(repos)} repos")

    for repo in repos:
        name = repo["name"]
        owner = repo["owner"]["login"]

        print(f"Processing: {name}")

        try:
            contributors = get_contributors(owner, name)
            all_contributors.update(contributors)
        except Exception as e:
            print(f"Error in {name}: {e}")

        time.sleep(0.2)  # avoid rate limits

    # Optional: filter bots
    filtered = {c for c in all_contributors if "bot" not in c.lower()}

    print("\n=== Unique Contributors ===")
    for user in sorted(filtered):
        print(user)

    print(f"\nTotal unique contributors: {len(filtered)}")


if __name__ == "__main__":
    main()