# FÉWURA Prospecting OS

MVP local d’un agent de prospection B2B avec recherche Brave, collecte de coordonnées publiques, brouillons commerciaux et pipeline CRM SQLite.

## Démarrage

1. Copier `.env.example` vers `.env`.
2. Renseigner `BRAVE_SEARCH_API_KEY` avec la clé Brave.
3. Facultatif : renseigner `HUNTER_API_KEY` et `HUNTER_MAX_LOOKUPS` pour l’enrichissement d’e-mails professionnels.
4. Lancer `npm start`.
5. Ouvrir `http://localhost:3000`.

## Brouillons Gmail

L’application peut créer un vrai brouillon Gmail au format HTML, avec le logo FÉWURA et les liens cliquables, grâce à OAuth 2.0. Elle n’utilise pas de mot de passe Gmail.

1. Dans Google Cloud Console, créer un client OAuth de type « Application Web ».
2. Ajouter `http://localhost:3000/auth/gmail/callback` comme URI de redirection autorisée.
3. Renseigner dans `.env` : `GMAIL_ACCOUNT`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` et `GMAIL_REDIRECT_URI`.
4. Ouvrir `http://localhost:3000/auth/gmail` et autoriser la boîte professionnelle.
5. Dans la fiche d’un prospect, utiliser « Créer le brouillon Gmail ».

Le jeton OAuth est conservé uniquement dans `data/gmail-token.json`, qui est exclu du dépôt Git.

La clé Brave est utilisée uniquement côté serveur. Elle n’est pas envoyée au navigateur.

## Fonctionnement

- Le ciblage se fait par région et profession.
- L’API Recherche d’entreprises fournit d’abord les établissements, la raison sociale, l’adresse, le SIREN/SIRET et l’activité lorsque la recherche géographique est disponible.
- OpenStreetMap/Overpass complète la liste avec les commerces locaux et les coordonnées publiées dans les tags OSM.
- Brave Search renvoie les sites officiels, les pages locales et les annuaires pertinents.
- L’exploration du site suit les pages Contact, équipe, agence et coordonnées.
- Hunter est utilisé uniquement en dernier recours lorsqu’un domaine d’entreprise est identifié et qu’aucun e-mail public n’a été trouvé sur le site. La clé est facultative et le nombre de recherches est plafonné par `HUNTER_MAX_LOOKUPS`.
- Pour les métiers locaux, plusieurs variantes de recherche sont lancées puis dédupliquées afin d’améliorer la couverture.
- L’agent inspecte un nombre limité de pages et extrait les e-mails et téléphones visibles publiquement lorsqu’ils sont présents.
- Un résultat n’est conservé que s’il possède au moins un e-mail public et au moins un signal métier cohérent avec l’offre FÉWURA : gestion/opérations, clients/commercial ou pilotage.
- Les collectivités et organismes publics clairement identifiés (mairies, préfectures, ministères, services publics, etc.) sont exclus sans bloquer les entreprises privées qui parlent par exemple d’« administration de biens ».
- Les entreprises sans e-mail ou sans signaux d’adéquation sont rejetées avant l’affichage et comptabilisées dans le retour de recherche.
- Chaque prospect conserve ses sources séparées (registre officiel, OSM, Brave, site exploré, Hunter), son extrait, sa date de collecte et un niveau de confiance.
- L’ajout au CRM est manuel depuis les résultats.
- Le CRM permet de faire avancer un prospect dans les colonnes Nouveaux, Qualifiés, Contactés, Réponses et Rendez-vous.
- Le générateur crée un brouillon à partir des informations enregistrées. Aucun e-mail n’est envoyé automatiquement : l’envoi reste soumis à la validation dans Gmail.

## Limites actuelles du MVP

- La qualification de l’entreprise et l’extraction de coordonnées restent à vérifier humainement.
- Le nom de l’entreprise est repris du titre du résultat Brave ; il ne constitue pas une preuve juridique d’identité.
- Les e-mails sont générés par modèle déterministe à partir des faits enregistrés, sans ajout de besoin supposé.
- Le suivi des ouvertures/réponses, l’authentification des utilisateurs et les rôles restent à ajouter avant une mise en production.

## Prospection responsable

L’application inclut une liste d’opposition locale (`opt_out`), une source par prospect et une validation humaine avant contact. Il faut compléter le dispositif par les mentions d’information, la procédure d’exercice des droits et les règles adaptées à la cible. La CNIL rappelle notamment que la prospection B2B par voie électronique peut relever de l’intérêt légitime lorsque la sollicitation est en rapport avec la profession, mais que la personne doit être informée et pouvoir s’opposer simplement : https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel
