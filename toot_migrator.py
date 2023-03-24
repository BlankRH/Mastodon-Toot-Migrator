import json
import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Union
import html2text
from mastodon import Mastodon, MastodonAPIError


def read_file(filepath):
    if not os.path.exists(filepath):
        raise FileExistsError(filepath + " does not exist. ")
    with open(filepath, "r") as f:
        return f.read()


class MastodonMigrator():

    mastodon = None
    data = None
    email = ""
    password = ""
    api_base_url = ""
    archive_path = "archive"

    def __init__(self):
        logging.debug("Loading settings...")
        self._load_settings()
        if not os.path.exists('pytooter_clientcred.secret'):
            logging.debug("Create app " + self.app_name)
            self.create_app()
        self.mastodon = Mastodon(client_id='pytooter_clientcred.secret',)
        logging.debug("Log in with email" + self.email)
        self.log_in()

    def _load_settings(self):
        params = json.loads(read_file("settings.json"))
        self.email = params["email"]
        self.password = params["password"]
        self.api_base_url = params["api_base_url"]
        self.app_name = params["app_name"]
        self.archive_path = params["archive_path"]

    def create_app(self):
        Mastodon.create_app(
            app_name=self.app_name,
            api_base_url=self.api_base_url,
            to_file='pytooter_clientcred.secret'
        )

    def log_in(self):
        self.mastodon.log_in(
            self.email,
            self.password,
            to_file='pytooter_usercred.secret'
        )

    def toot_batch(self, visibility, upload_media):
        f = open("log.txt", "a")
        cnt = 0
        fails = []
        for t in self.data:
            media_ids = []
            if upload_media:
                for a in t["attachments"]:
                    path = os.path.join(self.archive_path, a["url"][1:])
                    id = self._upload_media(path, a["mediaType"])
                    media_ids.append(id)
            res = self._toot_single(t["payload"], visibility, media_ids,
                                    t["sensitive"], t["spoiler_text"])
            cnt += 1
            print("\r", end="")
            print("Progress: {}/{}: ".format(
                cnt, len(self.data)), "▋" * (cnt // len(self.data)*100), end="")
            sys.stdout.flush()
            time.sleep(0.05)
            if not res[0]:
                fails.append((t["id"], res[1]))
            else:
                f.write(t["id"])
                f.write("\n")

    def _toot_single(self, payload, visibility, media_ids, sensitive, spoiler_text):
        try:
            self.mastodon.status_post(
                payload, media_ids=media_ids, visibility=visibility, sensitive=sensitive, spoiler_text=spoiler_text)
            return (True, None)
        except MastodonAPIError as e:
            return (False, e.__str__)

    def _upload_media(self, filepath, mime_type):
        with open(filepath, "rb") as f:
            data = f.read()
            d = self.mastodon.media_post(
                media_file=data, mime_type=mime_type)
        return d["id"]

    def import_data(self, limit: int, upload_list_path: str) -> None:
        self.data = read_outbox(self.archive_path, limit, upload_list_path)
        if len(self.data) == 0:
            logging.warning("Nothing to upload. ")

    def set_data(self, data: List[Dict[str, Union[str, list]]]) -> None:
        self.data = data


def read_outbox(archive_path, limit, upload_list_path) -> List[Dict[str, Union[str, list]]]:
    if not os.path.isdir(archive_path):
        raise FileNotFoundError("Cannot find directory " + archive_path)
    archive_path = os.path.join(archive_path, "outbox.json")
    logging.debug("Read toot data from " + archive_path)
    raw = read_file(archive_path)
    upload_list = None
    if upload_list_path:
        logging.debug("Read upload list from " + upload_list_path + ".")
        upload_list = set(read_file(upload_list_path).splitlines())
        if len(upload_list) == 0:
            logging.warning("No toot found in " + upload_list_path + ".")
    return parse_outbox(raw, limit, upload_list)


def parse_outbox(raw, limit, upload_list):
    d = json.loads(raw)
    items = d['orderedItems']
    res = []
    if limit == -1:
        limit = len(items)
    ignore = set()
    try:
        ignore = set(read_file("log.txt").splitlines())
    except:
        pass

    for item in items:
        if len(res) == limit:
            break
        if item['id'] in ignore:
            continue
        if upload_list and item['id'] not in upload_list:
            continue
        time = item['published']
        content = html2text.html2text(item['object']['content'])

        medias = []
        attachment = item['object']['attachment']
        if len(attachment):
            for a in attachment:
                medias.append(a)
        payload = "[{}]\n{}".format(
            time, content)
        d = {
            "id": item['id'],
            "payload": payload,
            "attachments": medias,
            "sensitive": item['object']["sensitive"],
            "spoiler_text": item['object'].get("spoiler_text", "")
        }
        res.append(d)
    return res


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number", type=int,
                        help="the amount of toots to upload; upload all if not specified", required=False, default=-1)
    parser.add_argument("-v", "--visibility", choices=['private', 'public', 'unlisted', 'direct'],
                        help="the visibility of uploaded toot; direct if not specified", required=False, default="direct")
    parser.add_argument("-l", "--upload-list",
                        help="a file in which every line is an id of a toot to be uploaded", required=False, default=None)
    parser.add_argument(
        '--media', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        '--verbose', action=argparse.BooleanOptionalAction, default=False)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    migrator = MastodonMigrator()
    migrator.import_data(args.number, args.upload_list)

    migrator.toot_batch(args.visibility, args.media)
