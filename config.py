#!/usr/bin/env python3
"""Fiche lisible des réglages du routeur (lecture seule : operation=read/load)."""
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from tplinkrouterc6u import TplinkRouterProvider
from espvault import EspVault

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Formulaires de réglages de l'AX53 (relevés dans ses JS) : ni état, ni clients/DHCP (rôle de report.py), ni actions.
FORMS = {
    'network': ['lan_ipv4', 'lan_ipv6', 'lan_agg', 'lan_jumbo_frame', 'mac_clone_advanced',
                'wan_dohdot', 'wan_backup_enable', 'routes_static'],
    'dhcps': ['setting'],
    'wireless': ['wireless_2g', 'wireless_5g', 'guest_2g', 'guest_5g', 'guest_2g5g', 'wireless', 'wireless_multi', 'wireless_addition_setting', 'smart_connect', 'ofdma',
                 'ofdma_mimo', 'twt', 'region', 'eco', 'smart_antenna'],
    'wireless_schedule_v2': ['settings'],
    'portal': ['portal'],
    'eco_mode': ['settings'],
    'afc': ['settings'],
    'nat': ['setting', 'alg', 'dmz', 'vs', 'pt'],
    'upnp': ['enable', 'service'],
    'ddns': ['provider', 'tplink', 'noip', 'dyndns'],
    'access_control': ['enable', 'mode', 'black_list'],
    'imb': ['setting'],
    'security_settings': ['new_enable'],
    'iot_security': ['enable', 'isolated_list'],
    'iptv': ['setting', 'udp_proxy_setting'],
    'smart_network': ['client_speed_limit', 'game_accelerator'],
    'vpn': ['enable', 'server', 'ovpn', 'wireguard', 'thirdvpn', 'vpn_user_list'],
    'openvpn': ['config'],
    'pptpd': ['config', 'accounts'],
    'l2tpoveripsec': ['config'],
    'wireguard': ['config', 'account'],
    'vpnconn': ['config'],
    'yandex_dns': ['enable'],
    'easymesh': ['easymesh_enable'],
    'administration': ['local', 'remote', 'https', 'mode', 'recovery', 'usersetting'],
    'time': ['settings', 'dst', 'hour24'],
    'ledgeneral': ['setting'],
    'ledpm': ['setting'],
    'system': ['sysmode'],
    'wol': ['device'],
    'ffs': ['config'],
}
# Type de connexion WAN actif -> formulaire de ses réglages
WAN4 = {'dhcp': 'wan_ipv4_dynamic', 'static': 'wan_ipv4_staticip', 'pppoe': 'wan_ipv4_pppoe',
        'l2tp': 'wan_ipv4_l2tp', 'pptp': 'wan_ipv4_pptp'}
WAN6 = {'dhcp6c': 'wan_ipv6_dynamic', 'staticv6': 'wan_ipv6_static', 'pppoev6': 'wan_ipv6_pppoe',
        '6to4': 'wan_ipv6_tunnel', 'passthrough': 'wan_ipv6_pass'}
# Comptes et mots de passe : jamais écrits dans la fiche
SECRET = re.compile(r'(^|_)(pwd|password|acc|username|private_key|psk_key|wpa_key|wep_key\d)$')


# Formulaires dont le champ enable n'est pas l'interrupteur de la section
ENABLE_NOT_MASTER = {'wireless_addition_setting'}


def is_off(data):
    return isinstance(data, dict) and str(data.get('enable', data.get('enabled'))) in ('off', 'False', '0')


def strip_secrets(data):
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if not SECRET.search(k)}
    if isinstance(data, list):
        return [strip_secrets(r) for r in data]
    return data


def wan_forms(client):
    v4 = read_form(client, 'admin/network?form=wan_ipv4_status') or {}
    v6 = read_form(client, 'admin/network?form=wan_ipv6_status') or {}
    forms = [WAN4.get(v4.get('conntype'))]
    if v6.get('enable') == 'on':
        forms.append(WAN6.get(v6.get('conntype')))
    return [f for f in forms if f]


def read_form(client, path):
    for op in ('read', 'load'):
        try:
            data = client.request(path, f'operation={op}')
            data = strip_secrets(data)
            if data not in (None, {}, []):
                return data
        except Exception:
            pass
    return None


def to_md(data):
    if isinstance(data, list) and data and all(isinstance(r, dict) for r in data):
        keys = list(dict.fromkeys(k for r in data for k in r))
        lines = ['| ' + ' | '.join(keys) + ' |', '|' + '---|' * len(keys)]
        lines += ['| ' + ' | '.join(str(r.get(k, '')) for k in keys) + ' |' for r in data]
        return '\n'.join(lines)
    if isinstance(data, dict):
        return '\n'.join(f'- **{k}** : {v}' for k, v in data.items())
    return f'```\n{data}\n```'


def main():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    url = os.getenv('ROUTER_URL', 'http://192.168.1.1')
    out = os.path.expanduser(os.getenv('CONFIG_FILE', os.path.join(SCRIPT_DIR, 'router-config.md')))
    client = TplinkRouterProvider.get_client_safe(url, EspVault().get_secret('router'), timeout=5)

    lines, empty = [f'# Configuration routeur ({url}) — {datetime.now():%Y-%m-%d %H:%M}'], []
    try:
        FORMS['network'][5:5] = wan_forms(client)
        for module, forms in FORMS.items():
            section = []
            for form in forms:
                data = read_form(client, f'admin/{module}?form={form}')
                if data is None:
                    empty.append(f'{module}/{form}')
                elif is_off(data) and form not in ENABLE_NOT_MASTER:
                    section += [f'### {form}', '- désactivé', '']
                else:
                    section += [f'### {form}', to_md(data), '']
            if section:
                lines += [f'## {module}'] + section
    finally:
        client.logout()

    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'{out} : {len(FORMS) and sum(map(len, FORMS.values())) - len(empty)} formulaires lus, {len(empty)} vides')


if __name__ == '__main__':
    main()
