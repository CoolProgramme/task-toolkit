import argparse
import os
import requests
import pandas as pd
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


def get_repo_info(repo):
    a = repo.find("h3").find("a")
    href = a.get("href")
    title = a.get_text(strip=True) if a else ""

    p = repo.find("p", attrs={"itemprop": "description"})
    description = p.get_text(strip=True) if p else ""

    span = repo.find("span", attrs={"itemprop": "programmingLanguage"})
    programming_language = span.get_text(strip=True) if span else ""

    return title, f"https://github.com{href}", description, programming_language


def get_proxies(proxies):
    return {"http": proxies} if proxies else None


def setup_retry_strategy():
    return HTTPAdapter(max_retries=Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    ))


def create_data_directory():
    current_dir = os.getcwd()
    dir_name = os.path.join(current_dir, "data", "github", "star")
    os.makedirs(dir_name, exist_ok=True)
    return dir_name


def backups(name, proxies):
    if not name:
        print(f"--name GitHub用户名是必须的！")
        return

    params = {"tab": "stars"}
    session = requests.Session()
    session.mount("https://", setup_retry_strategy())
    data = []

    while True:
        try:
            r = session.get(f"https://github.com/{name}", proxies=get_proxies(proxies), params=params)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            user_starred_repos = soup.find(id="user-starred-repos")
            repos = user_starred_repos.find_all(
                class_="col-12 d-block width-full py-4 border-bottom color-border-muted")

            for repo in repos:
                title, href, description, programming_language = get_repo_info(repo)
                data.append([title, programming_language, href, description])
                print(f"标题：{title}\n链接：{href}\n简介：{description}\n语言：{programming_language}\n")

            pagination = user_starred_repos.find("div", class_="paginate-container").find(
                attrs={"data-test-selector": "pagination"})
            btn_next = pagination and pagination.find("a", string="Next")
            if btn_next:
                parsed_url = urlparse(btn_next.get("href"))
                params["after"] = parse_qs(parsed_url.query).get("after", [None])[0]
            else:
                df = pd.DataFrame(data, columns=["标题", "语言", "链接", "简介"])
                df.to_excel(f"{create_data_directory()}/{datetime.now().strftime('%Y-%m-%d')}.xlsx", index=False)
                return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default=None, help="Specify the name")
    parser.add_argument("--proxies", type=str, default=None, help="Specify the proxies")
    args = parser.parse_args()
    backups(args.name, args.proxies)


if __name__ == '__main__':
    main()
