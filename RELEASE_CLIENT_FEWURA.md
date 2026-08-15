# Politique de release client FEWURA

Une build Windows n'est pas une release client tant que toute la chaîne suivante n'est pas validée :

1. tests cœur ;
2. compilation PyInstaller ;
3. test du vrai EXE compilé ;
4. signature Authenticode de l'EXE applicatif ;
5. vérification `Get-AuthenticodeSignature` = `Valid` ;
6. génération du Setup Inno Setup contenant l'EXE signé ;
7. signature Authenticode du Setup ;
8. vérification `Get-AuthenticodeSignature` = `Valid` ;
9. installation silencieuse du Setup dans un environnement Windows propre ;
10. test de l'application installée ;
11. vérification de la signature de l'EXE après installation ;
12. publication de l'artefact client uniquement si tout est vert.

## Signature de production

La release signée utilise Azure Artifact Signing (anciennement Trusted Signing) via l'action GitHub officielle `azure/trusted-signing-action`.

Secrets GitHub requis :

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_ARTIFACT_SIGNING_ENDPOINT`
- `AZURE_CODE_SIGNING_NAME`
- `AZURE_CERT_PROFILE_NAME`

Sans ces paramètres, le workflow `windows-signed-release.yml` doit échouer et aucune release client ne doit être publiée.

## SmartScreen

La signature publique est obligatoire pour toute distribution client directe. Elle ne doit jamais être remplacée par un certificat auto-signé ou par une instruction demandant au client de désactiver Defender/SmartScreen.

La réputation SmartScreen peut néanmoins nécessiter du temps pour une application distribuée directement. Pour les produits où l'exigence est l'absence du message SmartScreen dès la distribution, la voie privilégiée est la distribution MSIX via Microsoft Store, sous réserve de la création et validation du compte éditeur et de la soumission Store.

## Builds internes

Les workflows de build/test non signés peuvent rester disponibles uniquement pour développement et QA. Leur artefact doit être explicitement considéré comme interne et ne doit pas être envoyé aux clients.
