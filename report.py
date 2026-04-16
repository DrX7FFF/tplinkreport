#!/usr/bin/env python3
import os
import json
import getpass
from datetime import datetime
from dotenv import load_dotenv
from tplinkrouterc6u import TplinkRouterProvider, ClientException
from requests.exceptions import ConnectTimeout


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_existing(path):
    """
    Relit le tableau Markdown existant pour extraire, par MAC,
    les colonnes saisies manuellement : 'vu' et 'comment'.
    Format attendu : | Hostname | IP | Interface | DHCP | Réservé | Vu | MAC | Commentaire |
    """
    result = {}
    if not os.path.exists(path):
        return result
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('|') or '---' in line:
                continue
            cells = [c.strip() for c in line.split('|')]
            # cells[0] = '' (avant le premier |), cells[1..8], cells[9] = ''
            if len(cells) < 9:
                continue
            # Ignorer l'entête
            if cells[7].upper() == 'MAC':
                continue
            mac     = cells[7].upper()
            if mac:
                result[mac] = {
                    'hostname':  cells[1].strip(),
                    'ip':        cells[2].strip(),
                    'interface': cells[3].strip(),
                    'vu':        cells[6].strip(),
                    'comment':   cells[8].strip(),
                }
    return result

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

    # Union des 3 sources + historique existant
    all_macs = active_macs | set(reservation_macs.keys()) | set(existing.keys())

    for mac in all_macs:
        existing_entry = existing.get(mac, {})
        comment = existing_entry.get('comment', '')

        # Colonne Vu : X = exclu de surveillance (jamais écrasé)
        existing_vu = existing_entry.get('vu', '')
        if existing_vu.upper() == 'X':
            vu = 'X'
        elif mac in active_macs:
            vu = 'O'
        else:
            vu = 'N'

        # Hostname et IP : priorité clients connectés > baux > réservations > historique MD
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
        elif mac in reservation_macs:
            r = reservation_macs[mac]
            hostname  = r.hostname or ''
            ip        = str(r.ipaddr)
            interface = ''
        else:
            # Uniquement dans l'historique MD
            hostname  = existing_entry.get('hostname', '')
            ip        = existing_entry.get('ip', '')
            interface = existing_entry.get('interface', '')

        records[mac] = {
            'hostname':  hostname,
            'ip':        ip,
            'interface': interface,
            'dhcp':      'O' if mac in lease_macs else 'N',
            'reserved':  'O' if mac in reservation_macs else 'N',
            'vu':        vu,
            'comment':   comment,
        }

    return records

def save_md(records, path):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    count = len(records)
    lines = [
        f'# Carte réseau - {count} entrées - {now}',
        '',
        '| Hostname | IP | Interface | DHCP | Réservé | Vu | MAC | Commentaire |',
        '|---|---|---|:---:|:---:|:---:|---|---|',
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
            f"| {r['dhcp']} | {r['reserved']} | {r['vu']} | {mac} | {r['comment']} |"
        )

    lines.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

from tplinkrouterc6u import TplinkRouterProvider, AuthorizeError, ClientError

def main():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
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


    report_file = os.path.expanduser(os.getenv('REPORT_FILE', os.path.join(SCRIPT_DIR, 'network.md')))
    os.makedirs(os.path.dirname(report_file) or '.', exist_ok=True)

    existing = load_existing(report_file)
    records  = build_records(devices, leases, reservations, existing)

    save_md(records, report_file)

    print(f'Rapport généré : {report_file} ({len(records)} entrées)')

if __name__ == '__main__':
    main()