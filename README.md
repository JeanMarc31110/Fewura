# FEWURA PROSPECT V1

Agent de prospection B2B géolocalisée pour rechercher des entreprises à partir de sources publiques, qualifier les prospects et préparer des campagnes commerciales contrôlées.

## Fonctions

- recherche par zone géographique, rayon et catégorie ;
- mode « tous types d'entreprises » ;
- collecte de coordonnées professionnelles publiques ;
- enrichissement depuis les sites officiels ;
- déduplication ;
- scoring des prospects ;
- base SQLite locale ;
- export CSV/XLSX ;
- campagnes avec mode simulation par défaut ;
- envoi SMTP uniquement après activation explicite ;
- anti-double-envoi, limite quotidienne et liste `do_not_contact` ;
- interface FastAPI locale ;
- packaging Windows PRO PyInstaller + Inno Setup ;
- script de signature Authenticode FEWURA.

## Windows

Sur un PC Windows de développement :

```bat
CONSTRUIRE_SETUP_WINDOWS.bat
```

Le Setup final est généré dans `installer\output\`.

## Sécurité

Les secrets restent dans `.env` et ne doivent jamais être commités. L'application ne contourne ni CAPTCHA, ni authentification, ni protections anti-bot. L'envoi réel est désactivé par défaut.

## Version

FEWURA PROSPECT V1.0.0
