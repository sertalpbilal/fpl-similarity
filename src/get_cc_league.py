#%%
import requests
import json

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'DNT': '1',
    'FunctionKey': 'db059d47-8b44-476a-9dfc-509bceb87bee',
    'Origin': 'https://www.fplgameweek.com',
    'Pragma': 'no-cache',
    'Referer': 'https://www.fplgameweek.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

params = {
    'leagueId': 'special_10002',
    'entry': '275269',
    'compareEntry': '4845',
    'currentweek': '38',
    'doNotCache': '1',
    'refreshEntry': '0',
    'filterFrom': '0',
    'filterTo': '0',
    'liveFeedEventTimestamp': 'undefined',
    'fetchMoreTeams': 'undefined',
    'prevSeasonNum': '1',
    'sortOrder': 'orderByTotal',
    'currentPage': '1',
    'countryIso': '',
}

#%%
response = requests.get(
    'https://fontendfunctionsnortheuropenew.azurewebsites.net/api/LeagueFunction',
    params=params,
    headers=headers,
)

main_data = response.json()

params['currentPage'] = 2

response = requests.get(
    'https://fontendfunctionsnortheuropenew.azurewebsites.net/api/LeagueFunction',
    params=params,
    headers=headers,
)

main_data['TeamDatas'] = main_data['TeamDatas'] + response.json()['TeamDatas']

# %%
len(main_data['TeamDatas'])

with open('../data/list/cc_league.json', 'w') as f:
    json.dump(main_data, f, indent=4)
