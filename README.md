# tplinkreport

Génère un rapport de la carte réseau à partir d'un routeur TP-Link Archer.

Interroge le routeur pour récupérer les clients connectés, les baux DHCP et les réservations DHCP, puis produit un fichier `network.md` servant à la fois de rapport consultable et de source de vérité persistante.

## Compatibilité

Testé sur **TP-Link Archer AX53 v1.0**. Devrait fonctionner sur tout routeur supporté par la bibliothèque [tplinkrouterc6u](https://github.com/AlexandrErohin/TP-Link-Archer-C6U).

## Installation
```bash
git clone https://github.com/DrX7FFF/tplinkreport
cd tplinkreport
install.sh
```

## Configuration

La configuration est optionnelle. Sans fichier `.env`, le script utilise les valeurs par défaut et demande le mot de passe au lancement.

Pour éviter de ressaisir les paramètres à chaque fois, créer un fichier `.env` dans le dossier du script :
```
ROUTER_URL=http://192.168.1.1
ROUTER_PASSWORD=votre_mot_de_passe
REPORT_FILE=~/tplinkreport/network.md
```

| Variable | Défaut | Description |
|---|---|---|
| `ROUTER_URL` | `http://192.168.1.1` | URL de l'interface web du routeur |
| `ROUTER_PASSWORD` | _(demandé au lancement)_ | Mot de passe du routeur |
| `REPORT_FILE` | `network.md` dans le dossier du script | Chemin complet du fichier rapport |

## Utilisation
```bash
source .venv/bin/activate
python3 report.py
```

## Fichier généré

`network.md` — tableau Markdown trié par IP, servant à la fois de rapport consultable et de source de vérité. Relu à chaque lancement pour conserver les colonnes `Vu` et `Commentaire` modifiées manuellement. Les équipements déjà connus restent dans le rapport même après expiration de leur bail DHCP.

## Colonnes du rapport

| Colonne | Description |
|---|---|
| Hostname | Nom de l'appareil tel que retourné par le routeur |
| IP | Adresse IP |
| Interface | `Wired`, `2G`, `5G` |
| DHCP | `O` si un bail DHCP est actif, `N` sinon (IP statique probable) |
| Réservé | `O` si une réservation MAC→IP est configurée sur le routeur |
| Vu | `O` si l'équipement est actuellement sur le réseau, `N` sinon, `X` pour exclure la surveillance |
| MAC | Adresse MAC |
| Commentaire | Champ libre, à renseigner manuellement dans `network.md`, conservé entre les lancements |

### Colonne Vu — valeur `X`

Mettre `X` dans la colonne `Vu` pour un équipement permet d'exclure sa surveillance : la valeur ne sera jamais mise à jour (ni `O` ni `N`), ce qui évite le bruit dans les diffs git pour les appareils épisodiques (PC portable, téléphone invité…). Le hostname, l'IP et le commentaire restent quant à eux toujours mis à jour normalement.