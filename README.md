# tplinkreport

Génère un rapport de la carte réseau à partir d'un routeur TP-Link Archer.

Interroge le routeur pour récupérer les clients connectés, les baux DHCP et les réservations DHCP, puis produit un fichier `network.json` (référence persistante) et un fichier `network.md` (consultation).

## Compatibilité

Testé sur **TP-Link Archer AX53 v1.0**. Devrait fonctionner sur tout routeur supporté par la bibliothèque [tplinkrouterc6u](https://github.com/AlexandrErohin/TP-Link-Archer-C6U).

## Installation
```bash
git clone https://github.com/DrX7FFF/tplinkreport
cd tplinkreport
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

La configuration est optionnelle. Sans fichier `.env`, le script utilise les valeurs par défaut et demande le mot de passe au lancement.

Pour éviter de ressaisir les paramètres à chaque fois, créer un fichier `.env` à la racine du projet :
```
ROUTER_URL=http://192.168.1.1
ROUTER_PASSWORD=votre_mot_de_passe
REPORT_PATH=~/tplinkreport
```

| Variable | Défaut | Description |
|---|---|---|
| `ROUTER_URL` | `http://192.168.1.1` | URL de l'interface web du routeur |
| `ROUTER_PASSWORD` | _(demandé au lancement)_ | Mot de passe du routeur |
| `REPORT_PATH` | `.` | Dossier de sauvegarde des rapports |

## Utilisation
```bash
source .venv/bin/activate
python3 report.py
```

## Fichiers générés

- `network.json` — données complètes, relu à chaque lancement pour conserver les commentaires
- `network.md` — tableau Markdown trié par IP, pour consultation

## Colonnes du rapport

| Colonne | Description |
|---|---|
| Hostname | Nom de l'appareil tel que retourné par le routeur |
| IP | Adresse IP |
| Interface | `Wired`, `2G`, `5G` |
| DHCP | `O` si un bail DHCP est actif, `N` sinon (IP statique probable) |
| Réservé | `O` si une réservation MAC→IP est configurée sur le routeur |
| Dernière vue | Dernière fois que l'appareil était connecté ou avait un bail actif |
| MAC | Adresse MAC |
| Commentaire | Champ libre, à renseigner manuellement dans `network.json`, conservé entre les lancements |