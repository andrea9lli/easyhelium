import argparse
import requests
import sys

from datetime import datetime
from datetime import timedelta

from pycoingecko import CoinGeckoAPI
from rich.console import Console
from rich.progress import Progress
from rich.table import Table


__author__ = "a9lli"
__copyright__ = "a9lli"
__license__ = "MIT"


TIMESPANS = {
    '24h': timedelta(days=1), 
    '48h': timedelta(days=2), 
    '7d': timedelta(days=7), 
    '14d': timedelta(days=14),
    '30d': timedelta(days=30) 
}

CURRENCIES = {
    'eur': '€',
    'usd': '$'
}


def beautify(h: dict):
    console = Console()

    name = ' '.join(h["name"].split('-')).title()
    console.print(f'Name: [bold red]{name}[/bold red]')

    if 'online' in h['status']:
        status = ':green_circle:'
    else:
        status = ':red_circle:'
    console.print(f'Status: {status}')

    reward_scale = h["reward_scale"]
    if reward_scale >= 75:
        reward_color = 'green'
    elif reward_scale >= 50:
        reward_color = 'yellow'
    else:
        reward_color = 'red'
    console.print(f'Reward scale: [bold {reward_color}]{reward_scale} %'
                  f'[/bold {reward_color}]')

    console.print(f'Witnesses: {h["witnesses"]}')

    currency = h['currency']
    cg = CoinGeckoAPI()
    crcy = cg.get_price(ids='helium', vs_currencies=currency).get('helium').get(currency)

    hnt_reward_last = round(h["rewards_last"], 3)
    eur_reward_last = round(crcy*hnt_reward_last, 2)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date")
    table.add_column("Reward amount", justify="center")
    table.add_column("Reward type", justify="center")

    for r in h['rewards']:
        table.add_row(
            f'{r["time"]}',
            f'[bold]{round(r["amount"], 3):.3f}[/bold] HNT',
            r["type"]
            )

    console.print(table)

    console.print(f'Total reward in last {h["last"].days} days: '
                  f'{hnt_reward_last} HNT ({eur_reward_last}{CURRENCIES[currency]})')
    console.print()


def do_magic(args, progress):
    base_url = f'https://api.helium.io/v1/hotspots/{args.wallet_id}'
    activity_url = f'{base_url}/activity'
    witness_url = f'{base_url}/witnesses'

    task = progress.add_task("[red]Fetching wallet data...", total=100)

    r = requests.get(base_url)
    data = r.json().get('data')
    if data.get('error'):
        print('Invalid wallet id.')
        return
    progress.update(task, advance=25)

    r = requests.get(witness_url)
    witnesses = len(r.json().get('data'))
    progress.update(task, advance=50)

    hotspot = {
        'name': data['name'],
        'status': data['status']['online'],
        'reward_scale': round(data['reward_scale'] * 100, 2),
        'witnesses': witnesses,
        'rewards': []
    }

    r = requests.get(activity_url)
    cursor = r.json().get('cursor')
    progress.update(task, advance=75)
    r = requests.get(activity_url, params={'cursor': cursor})
    data = r.json().get('data')
    reward_amount_last = 0.
    for d in data:
        if 'rewards' in d.keys():
            reward_time = datetime.fromtimestamp(d['time'])
            if reward_time < datetime.today() - TIMESPANS[args.last]:
                break
            reward_amount = d['rewards'][0]['amount'] / 10 ** 8
            reward_type = d['rewards'][0]['type']
            hotspot['rewards'].append({
                'time': reward_time,
                'type': reward_type,
                'amount': reward_amount
            })
            reward_amount_last += reward_amount
    hotspot['rewards_last'] = reward_amount_last
    hotspot['last'] = TIMESPANS[args.last]
    hotspot['currency'] = args.currency
    progress.update(task, advance=100)
    return hotspot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f'Track your Helium '
                                                 f'wallet activities')
    parser.add_argument(dest='wallet_id',
                        help="Helium wallet ID",
                        type=str)
    parser.add_argument('--last',
                    choices=['24h', '48h', '7d', '14d', '30d'],
                    default='24h',
                    help='Select between different time periods')
    parser.add_argument('--currency',
                    choices=['eur', 'usd'],
                    default='eur',
                    help='Choose preferred currency')

    args = parser.parse_args(sys.argv[1:])
    with Progress(transient=True) as progress:
        hotspot = do_magic(args, progress)
    beautify(hotspot)
