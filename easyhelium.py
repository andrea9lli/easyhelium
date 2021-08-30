import argparse
import sys
from datetime import datetime
from datetime import timedelta

import requests

__author__ = "a9lli"
__copyright__ = "a9lli"
__license__ = "MIT"

from rich.console import Console
from rich.progress import Progress


def beautify(h: dict):
    console = Console()
    console.print('-' * 64)

    console.print(h['name'], style='bold red')

    if 'online' in h['status']:
        status = f'[bold green]{h["status"]}[/bold green]'
    else:
        status = f'[bold red]{h["status"]}[/bold red]'
    console.print(f'Status: {status}')

    reward_scale = h["reward_scale"]
    if reward_scale >= 75:
        reward_color = 'green'
    elif reward_scale >= 50:
        reward_color = 'yellow'
    else:
        reward_color = 'red'
    console.print(f'Reward scale: [bold {reward_color}]{reward_scale}%'
                  f'[bold {reward_color}]')

    console.print(f'Witnesses: {h["witnesses"]}')
    console.print('-' * 64)

    for r in h['rewards']:
        console.print(f'[magenta][{r["time"]}][/magenta]\t'
                      f'{round(r["amount"], 2)} HNT\t{r["type"]}')
    console.print('-' * 64)
    console.print(f'Total reward in last 24h: '
                  f'{round(h["rewards_last24"], 2)} HNT')
    console.print('-' * 64)


def do_magic(args):
    base_url = f'https://api.helium.io/v1/hotspots/{args.wallet_id}'
    activity_url = f'{base_url}/activity'
    witness_url = f'{base_url}/witnesses'

    r = requests.get(base_url)
    data = r.json().get('data')

    r = requests.get(witness_url)
    witnesses = len(r.json().get('data'))

    hotspot = {
        'name': data['name'],
        'status': data['status']['online'],
        'reward_scale': round(data['reward_scale'] * 100, 2),
        'witnesses': witnesses,
        'rewards': []
    }

    r = requests.get(activity_url)
    cursor = r.json().get('cursor')
    r = requests.get(activity_url, params={'cursor': cursor})
    data = r.json().get('data')
    reward_amount_last24 = 0.
    for d in data:
        if 'rewards' in d.keys():
            reward_time = datetime.fromtimestamp(d['time'])
            if reward_time < datetime.today() - timedelta(days=1):
                break
            reward_amount = d['rewards'][0]['amount'] / 10 ** 7
            reward_type = d['rewards'][0]['type']
            hotspot['rewards'].append({
                'time': reward_time,
                'type': reward_type,
                'amount': reward_amount
            })
            reward_amount_last24 += reward_amount
    hotspot['rewards_last24'] = reward_amount_last24
    return hotspot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f'Track your Helium '
                                                 f'wallet activities')
    parser.add_argument(dest='wallet_id',
                        help="Helium wallet ID",
                        type=str)
    args = parser.parse_args(sys.argv[1:])
    with Progress(transient=True) as progress:
        task = progress.add_task(description='Fetching data...', start=False)
        hotspot = do_magic(args)
    beautify(hotspot)
