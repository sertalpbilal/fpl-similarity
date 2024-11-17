import requests
import json
import os
import time
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

season = '2024-2025'

picks_url = "https://fantasy.premierleague.com/api/entry/{team_id}/event/{gameweek}/picks/"
transfer_url = "https://fantasy.premierleague.com/api/entry/{team_id}/transfers/"


def get_next_gw():
    next_gw = 1
    r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
    for event in r['events']:
        if event['is_next']:
            next_gw = event['id']
            break
    else:
        next_gw = 39

    ng = {'next_gw': next_gw}
    with open('../data/info.json', 'w') as f:
        json.dump(ng, f, indent=4)
    return next_gw


def fetch_data(url, params=None):
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching {url}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching {url}: {e}")
        return None


def download_picks():
    pf = f'../data/entries/{season}/'
    pathlib.Path(pf).mkdir(exist_ok=True, parents=True)

    next_gw = get_next_gw()
    print(f"Next GW is {next_gw}")

    with open(f"../data/list/cc_league_{season}.json", encoding="utf-8") as f:
        raw_data = json.load(f)
    teams = [{
        'id': e['EntryId'],
        'Name': e['Name'],
        'PlayerName': e['PlayerName'],
        'Description': e['Description'],
    } for e in raw_data['TeamDatas']]

    with open('../index.json', 'w', encoding='utf-8') as f:
        json.dump(teams, f, indent=4)

    tasks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        with tqdm(total=len(teams) * (next_gw - 1 + 1)) as progress_bar:
            for cc in teams:
                for gw in range(1, next_gw):
                    fname = f"../data/entries/{season}/{cc['id']}_{gw}.json"
                    if not os.path.exists(fname):
                        tasks.append(executor.submit(fetch_and_save, picks_url.format(team_id=cc['id'], gameweek=gw), fname, f"{cc['id']} GW{gw}", progress_bar))

                # Add transfer tasks
                tr_fname = f"../data/entries/{season}/{cc['id']}_tr.json"
                if not os.path.exists(tr_fname):
                    tasks.append(executor.submit(fetch_and_save, transfer_url.format(team_id=cc['id']), tr_fname, f"{cc['id']} Transfers", progress_bar))

            for future in as_completed(tasks):
                future.result()


def fetch_and_save(url, filename, description, progress_bar):
    data = fetch_data(url)
    if data:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved {description} to {filename}")
    progress_bar.update(1)


def combine_all():
    with open('../index.json') as f:
        cc_list = json.load(f)
    all_entries = []

    for cc in cc_list:
        cc_id = cc['id']
        entry = {'id': cc_id, 'picks': {}}

        for gw in range(1, 39):
            fname = f"../data/entries/{season}/{cc_id}_{gw}.json"
            if os.path.exists(fname):
                with open(fname) as f:
                    gw_picks = json.load(f)
                entry['picks'][gw] = [[e['element'], e['multiplier']] for e in gw_picks['picks']]

        tr_fname = f"../data/entries/{season}/{cc_id}_tr.json"
        if os.path.exists(tr_fname):
            with open(tr_fname) as f:
                transfers = json.load(f)
            entry['trs'] = [[e['element_out'], e['element_in'], e['event'], e['time']] for e in transfers]

        all_entries.append(entry)

    with open('../data/combined.json', 'w') as f:
        json.dump(all_entries, f, indent=4)


if __name__ == "__main__":
    download_picks()
    combine_all()
