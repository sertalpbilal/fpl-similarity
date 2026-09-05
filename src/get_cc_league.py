import requests
import json
import pathlib
import sys

season = '2026-2027'

API_URL = 'https://fplgameweekrestapi.azurewebsites.net/LeagueFunction'

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'FunctionKey': 'db059d47-8b44-476a-9dfc-509bceb87bee',
    'Origin': 'https://www.fplgameweek.com',
    'Referer': 'https://www.fplgameweek.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="152", "Not?A_Brand";v="24", "Brave";v="152"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

base_params = {
    'leagueId': 'special_10002',
    'entry': '3333334',
    'compareEntry': '4540256',
    'currentweek': '3',
    'doNotCache': '1',
    'refreshEntry': '0',
    'filterFrom': '0',
    'filterTo': '0',
    'prevSeasonNum': '1',
    'sortOrder': 'orderByTotal',
    'countryIso': '',
}


def get_current_gw():
    """Latest gameweek that has started, used for the `currentweek` parameter."""
    try:
        r = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=30).json()
        started = [e['id'] for e in r['events'] if e['is_current'] or e['finished']]
        return max(started) if started else 1
    except Exception as e:
        print(f"Could not read bootstrap-static ({e}), falling back to currentweek={base_params['currentweek']}")
        return int(base_params['currentweek'])


def fetch_page(page, current_gw):
    params = dict(base_params)
    params['currentweek'] = str(current_gw)
    params['currentPage'] = str(page)
    if page == 1:
        params['liveFeedEventTimestamp'] = 'undefined'
        params['fetchMoreTeams'] = 'undefined'
    else:
        params['liveFeedEventTimestamp'] = 'null'
        params['fetchMoreTeams'] = '0'

    response = requests.get(API_URL, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def main():
    current_gw = get_current_gw()
    print(f"Fetching content creator league for GW{current_gw}")

    main_data = fetch_page(1, current_gw)
    teams = main_data.get('TeamDatas') or []
    if not teams:
        print("Page 1 returned no teams, aborting without touching cached list.")
        print(json.dumps({k: v for k, v in main_data.items() if k != 'TeamDatas'}, indent=2, default=str)[:2000])
        sys.exit(1)

    # the API can return the same entry on two pages, and keeps serving the
    # last page for page numbers past the end, so stop once nothing new shows up
    seen = set()
    unique_teams = []

    def add_teams(page_teams):
        added = 0
        for t in page_teams:
            if t['EntryId'] in seen:
                continue
            seen.add(t['EntryId'])
            unique_teams.append(t)
            added += 1
        return added

    add_teams(teams)
    page = 2
    while page <= 10:
        page_data = fetch_page(page, current_gw)
        if add_teams(page_data.get('TeamDatas') or []) == 0:
            break
        page += 1

    main_data['TeamDatas'] = unique_teams
    print(f"Found {len(unique_teams)} unique teams over {page - 1} page(s)")

    pathlib.Path("../data/list/").mkdir(exist_ok=True, parents=True)
    with open(f'../data/list/cc_league_{season}.json', 'w', encoding='utf-8') as f:
        json.dump(main_data, f, indent=4)


if __name__ == "__main__":
    main()
