import argparse
import json
import os.path
import random
import re
import time
from hashlib import md5

import httpx
from loguru import logger
from lxml import etree

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.36",
}
headers2 = {
    "accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "referer": "https://www.pixiv.net/",
    "sec-fetch-dest": "image",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.36",
}
config = {"save_dir": "pixiv"}
task = []
def initArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", dest="start", type=int)
    parser.add_argument("-l", "--limit", dest="limit", type=int)
    parser.add_argument("mainUrl", type=str)
    args = parser.parse_args()
    config["homepage"] = args.mainUrl
    config["start"] = args.start or 0
    config["limit"] = args.limit or 999

def loadCookies():
    with open("cookie.txt") as fp:
        config["cookies"]={item.split("=")[0]: item.split("=")[1] for item in fp.read().split("; ")}
def searchUserInfo(nick):
    params = {
        "nick": nick,
        "s_mode": "s_usr",
    }
    response = httpx.get(
        "https://www.pixiv.net/search_user.php",
        headers=headers,
        params=params,
        follow_redirects=True,
        cookies=config["cookies"],
    )
    tree = etree.HTML(response.text)
    units = tree.xpath("//a[@class='title']")

    return [
        {"nick": units[n].text, "uid": units[n].attrib["href"].split("/")[2]}
        for n in range(len(units))
    ]


def getUserInfo(id):
    response = httpx.get(
        f"https://www.pixiv.net/ajax/user/{id}/profile/all",
        headers=headers,
        cookies=cookies,
    )
    content = json.loads(response.text)["body"]
    if response.status_code == 200:
        return {
            "userName": content["pickup"][0]["userName"],
            "illusts": list(content["illusts"].keys()),
        }


def getDetailInfo(id):
    response = httpx.get(
        f"https://www.pixiv.net/ajax/illust/{id}", headers=headers, cookies=cookies
    )
    if response.status_code == 200:
        content = json.loads(response.text)["body"]
        return {
            "id": content["id"],
            "title": content["title"],
            "date": content["createDate"].split("T")[0],
            "urls": content["urls"]["original"],
            "pageCount": content["pageCount"],
        }


def downloader(dst, urls):
    if not os.path.exists(dst):
        os.mkdir(dst)
        for url in urls:
            file=os.path.join(dst, url.split("/")[-1])
            if not os.path.exists(file):
                response = httpx.get(url, headers=headers2)
                if response.status_code == 200:
                    with open(dst, "wb") as fp:
                        fp.write(response.content)


def main(mainUrl):
    task_name = md5(mainUrl.encode("utf-8")).hexdigest()
    logger.info(f"任务:{task_name} {mainUrl}")
    try:
        if not os.path.exists(f"task/{task_name}.json"):
            uid = re.match("https://www.pixiv.net/users/(\d+)", mainUrl).group(1)
            username, illusts = getUserInfo(uid).values()
            if len(illusts) > 100:
                delay = 3
            else:
                delay = 0
            for illust in illusts:
                _, title, date, urls, pageCount = getDetailInfo(illust).values()
                logger.info(title)
                task.append(
                    {
                        "dst": os.path.join(config["save_dir"], date + title),
                        "urls": [
                            re.sub("_p\d+", f"_p{i}", urls) for i in range(0, pageCount)
                        ],
                    }
                )
                time.sleep(delay + random.random())
            with open(f"task/{task_name}.task") as fp:
                json.dump(task,fp)
        with open(f"task/{task_name}.task")    as fp:
            tasks=json.load(fp)
            for unit in tasks:
                downloader(task['dst'],task['urls'])


    except Exception as e:
        print(e)

if __name__ == '__main__':
    os.chdir(os.path.split(__file__)[0])
    loadCookies()
    initArgs()
    main(config["homepage"])
