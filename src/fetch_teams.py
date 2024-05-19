import requests
import json
import os
import glob
import time


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


def download_picks():

    # Find all finished GWs
    next_gw = get_next_gw()

    print(f"Next GW is {next_gw}")

    # Get Content Creator League Team Ids
    with open("../data/list/cc_league.json", encoding="utf-8") as f:
        raw_data = json.load(f)
    teams = [{
        'id': e['EntryId'],
        'Name': e['Name'],
        'PlayerName': e['PlayerName'],
        'Description': e['Description'],
        } for e in raw_data['TeamDatas']]
    with open('../index.json', 'w', encoding='utf-8') as f:
        json.dump(teams, f, indent=4)

    # Iterate over Creators and Gameweeks and cache their picks
    for cc in teams:
        for gw in range(1,next_gw):
            fname = f"../data/entries/{cc['id']}_{gw}.json"
            if os.path.exists(fname):
                print(f"Skipping {cc['id']} GW{gw}, data exists...")
                continue
            else:
                picks = requests.get(picks_url.format(team_id=cc['id'], gameweek=gw))
                if picks.status_code == 200:
                    picks = picks.json()
                else:
                    print(f"Error, skipping {cc['id']} GW{gw}")
                    continue
                print(f"Fetching {cc['id']} GW{gw}...")
                with open(fname, 'w') as f:
                    json.dump(picks, f, indent=4)
                    time.sleep(0.4)
        # Transfers needs to be replaced every tune
        fname = f"../data/entries/{cc['id']}_tr.json"
        trs = requests.get(transfer_url.format(team_id=cc['id']))
        if trs.status_code == 200:
            trs = trs.json()
        else:
            print(f"Error skipping {cc['id']} transfers")
            continue
        with open(fname, 'w') as f:
            json.dump(trs, f, indent=4)
            time.sleep(0.4)


def combine_all():
    with open('../index.json') as f:
        cc_list = json.load(f)
    all_entries = []
    for cc in cc_list:
        cc_id = cc['id']
        entry = {'id': cc_id, 'picks': {}}
        for gw in range(1,39):
            if os.path.exists(f"../data/entries/{cc_id}_{gw}.json"):
                with open(f"../data/entries/{cc_id}_{gw}.json") as f:
                    gw_picks = json.load(f)
                entry['picks'][gw] = [[e['element'], e['multiplier']] for e in gw_picks['picks']]
        if os.path.exists(f"../data/entries/{cc_id}_tr.json"):
            with open(f"../data/entries/{cc_id}_tr.json") as f:
                transfers = json.load(f)
            entry['trs'] = [[e['element_out'], e['element_in'], e['event'], e['time']] for e in transfers]
        
        all_entries.append(entry)

    with open('../data/combined.json', 'w') as f:
        json.dump(all_entries, f, indent=4)
    


if __name__ == "__main__":
    download_picks()
    combine_all()
