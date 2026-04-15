#!/usr/bin/env python3
import os
import json
import getpass
from datetime import datetime
from dotenv import load_dotenv
from tplinkrouterc6u import TplinkRouterProvider, ClientException
from requests.exceptions import ConnectTimeout

REPORT_JSON = 'network.json'
REPORT_MD   = 'network.md'

def load_existing(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def fetch_data(url, password):
    client = TplinkRouterProvider.get_client(url, password, timeout=5)
    client.authorize()
    status       = client.get_status()
    leases       = client.get_ipv4_dhcp_leases()
    reservations = client.get_ipv4_reservations()
    client.logout()
    return status.devices, leases, reservations

def normalize_mac(mac):
    return str(mac).upper()

def build_records(devices, leases, reservations, existing):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    records = {}

    lease_macs       = {normalize_mac(l.macaddr): l for l in leases}
    reservation_macs = {normalize_mac(r.macaddr): r for r in reservations}
    device_macs      = {normalize_mac(d.macaddr): d for d in devices}

    # MACs vues actives (connectées ou bail actif)
    active_macs = set(device_macs.keys()) | set(lease_macs.keys())

    # Union des 3 sources
    all_macs = active_macs | set(reservation_macs.keys())

    for mac in all_macs:
        existing_entry = existing.get(mac, {})
        comment   = existing_entry.get('comment', '')
        last_seen = now if mac in active_macs else existing_entry.get('last_seen', '')

        # Hostname et IP : priorité clients connectés > baux > réservations
        if mac in device_macs:
            d = device_macs[mac]
            hostname  = d.hostname or ''
            ip        = str(d.ipaddr)
            interface = d.type.value
        elif mac in lease_macs:
            l = lease_macs[mac]
            hostname  = l.hostname or ''
            ip        = str(l.ipaddr)
            interface = ''
        else:
            r = reservation_macs[mac]
            hostname  = r.hostname or ''
            ip        = str(r.ipaddr)
            interface = ''

        records[mac] = {
            'hostname':  hostname,
            'ip':        ip,
            'interface': interface,
            'dhcp':      'O' if mac in lease_macs else 'N',
            'reserved':  'O' if mac in reservation_macs else 'N',
            'last_seen': last_seen,
            'comment':   comment,
        }

    return records

def save_json(records, path):
    with open(path, 'w') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def save_md(records, path):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    count = len(records)
    lines = [
        f'# Carte réseau - {count} entrées - {now}',
        '',
        '| Hostname | IP | Interface | DHCP | Réservé | Dernière vue | MAC | Commentaire |',
        '|---|---|---|:---:|:---:|---|---|---|',
    ]

    def sort_key(item):
        try:
            return [int(x) for x in item[1]['ip'].split('.')]
        except Exception:
            return [999, 999, 999, 999]

    for mac, r in sorted(records.items(), key=sort_key):
        iface = r['interface'].replace('host_', '').upper() if r['interface'] else ''
        iface = iface.replace('WIRED', 'Wired')
        lines.append(
            f"| {r['hostname']} | {r['ip']} | {iface} "
            f"| {r['dhcp']} | {r['reserved']} | {r['last_seen']} | {mac} | {r['comment']} |"
        )

    lines.append('')
    with open(path, 'w') as f:
        f.write('\n'.join(lines))

from tplinkrouterc6u import TplinkRouterProvider, AuthorizeError, ClientError

def main():
    load_dotenv()
    url      = os.getenv('ROUTER_URL', 'http://192.168.1.1')
    password = os.getenv('ROUTER_PASSWORD') or getpass.getpass(f'Mot de passe routeur ({url}) : ')

    # print('Connexion au routeur...')
    try:
        devices, leases, reservations = fetch_data(url, password)
    except ConnectTimeout:
        print(f'Erreur : impossible de joindre le routeur ({url}).')
        return
    except ClientException:
        print('Erreur : mot de passe incorrect.')
        return


    global REPORT_JSON, REPORT_MD
    REPORT_PATH = os.path.expanduser(os.getenv('REPORT_PATH', '.'))
    REPORT_JSON = os.path.join(REPORT_PATH, REPORT_JSON)
    REPORT_MD   = os.path.join(REPORT_PATH, REPORT_MD)
    os.makedirs(REPORT_PATH, exist_ok=True)

    # print(f'  {len(devices)} clients connectés, {len(leases)} baux DHCP, {len(reservations)} réservations')

    existing = load_existing(REPORT_JSON)
    records  = build_records(devices, leases, reservations, existing)

    save_json(records, REPORT_JSON)
    save_md(records, REPORT_MD)

    print(f'Rapport généré : {REPORT_JSON}, {REPORT_MD} ({len(records)} entrées)')

if __name__ == '__main__':
    main()