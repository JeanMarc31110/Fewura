# FÉWURA CRM

CRM commercial Windows avec gestion des prospects et prospection.

## Version publiée

Le fichier [`FÉWURA CRM.exe`](./FÉWURA%20CRM.exe) contient l’interface native mise à jour :

- sélection multiple des entreprises ;
- sélection de tout le tableau ou d’un groupe ;
- suppression individuelle ou groupée ;
- validation groupée des e-mails ;
- prospection avec l’option **Toutes les activités** ;
- identité visuelle FÉWURA actualisée.

## Code source

Le code de l’application se trouve dans [`app/`](./app/). Pour lancer la partie serveur :

```powershell
cd app
npm install
node server.js
```

La configuration est à fournir dans `app/.env` à partir de `app/.env.example`. Les secrets et les données locales ne sont pas versionnés.

## Vérifications

- `node --check app/server.js`
- `python -m py_compile app/desktop_app.py`
- test API de validation de prospection avec activité vide et avec **Toutes les activités**
- test API des actions groupées de prospects
