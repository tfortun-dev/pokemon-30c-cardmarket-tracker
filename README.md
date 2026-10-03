# Pokémon 30C — Cardmarket FR tracker

Suivi automatisé des **191 cartes** du set Pokémon **30e Anniversaire / 30C**, à partir des annonces Cardmarket **françaises uniquement**.

## Mesures suivies
- prix FR le plus bas, tous états confondus ;
- médiane des 5 annonces FR les moins chères ;
- état de l'offre la moins chère et détail des 5 premières offres ;
- variations 1 h / 24 h / 7 j / 30 j ;
- plus bas / plus haut historiques ;
- alertes : ±10 % sur 24 h, ±20 % sur 7 j, nouveau plus bas, faible offre FR.

Le Price Guide, le Trend Price et les moyennes multilingues ne sont jamais utilisés.

## Automatisation
- `.github/workflows/scrape.yml` : Playwright toutes les heures à :07 + lancement manuel.
- `.github/workflows/pages.yml` : publication du tableau de bord après chaque mise à jour.
- `data/latest.json` : dernier état.
- `data/history/YYYY-MM-DD.json` : historique horaire compact.

Le scraper espace les requêtes de 10 secondes. En cas de 403/429/CAPTCHA ou si le filtre `language=2` n'est pas confirmé, il **n'enregistre pas de nouveau prix** et conserve les anciennes données comme périmées. Aucun contournement de protection n'est utilisé.

## Site
Une fois GitHub Pages activé, l'adresse est :
https://tfortun-dev.github.io/pokemon-30c-cardmarket-tracker/

Le bouton **Lancer une collecte** ouvre directement le workflow GitHub Actions pour pouvoir le déclencher depuis un téléphone.

## Limite
Cardmarket peut bloquer les IP de GitHub Actions. Le projet le signale explicitement plutôt que d'utiliser des données d'une autre langue.

> Automatisation initialisée : collecte horaire + publication GitHub Pages.
