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

### Développement

Sur un PC Windows de développement :

```bat
CONSTRUIRE_SETUP_WINDOWS.bat
```

Le Setup final est généré dans `installer\output\`.

### Installation professionnelle

#### Installation interactive
1. Téléchargez la dernière release depuis [GitHub Releases](https://github.com/JeanMarc31110/Fewura/releases)
2. Double-cliquez sur `Fewura_Setup_*.exe`
3. Suivez l'assistant d'installation
4. Fewura s'installe dans `C:\Program Files\Fewura`
5. Les raccourcis de bureau et du menu Démarrage sont créés automatiquement

#### Déploiement silencieux (sans interface)
```powershell
# Télécharger et installer depuis le script PowerShell
.\install-client-pro.ps1

# Avec token GitHub (pour authenticated requests)
.\install-client-pro.ps1 -Token "your-github-token"

# Ou utiliser le wrapper batch
install-client-pro.bat
```

#### Déploiement en masse (MDM, SCCM, etc.)
```batch
REM Installation avec options
Fewura_Setup_1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

REM Désinstallation
"C:\Program Files\Fewura\unins000.exe" /VERYSILENT /NORESTART
```

### Configuration du code-signing (optionnel)

Pour signer les exécutables avec votre certificat Authenticode :

1. **Ajouter les secrets GitHub :**
   - `WINDOWS_SIGNING_CERT_BASE64` : Votre certificat PFX encodé en base64
   - `WINDOWS_SIGNING_CERT_PASSWORD` : Le mot de passe du certificat

2. **Générer base64 du certificat :**
```powershell
$cert = [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes("C:\path\to\cert.pfx"))
$cert | Set-Clipboard
```

3. **Ajouter les secrets dans GitHub :**
   - Allez à `Settings` > `Secrets and variables` > `Actions`
   - Créez les deux secrets listés ci-dessus

Le pipeline CI/CD signera automatiquement les exécutables lors des releases.

**Note :** Les builds non signés sont réservés au développement. Ne demandez jamais aux clients de désactiver Windows Defender ou SmartScreen.

## Sécurité

Les secrets restent dans `.env` et ne doivent jamais être commités. L'application ne contourne ni CAPTCHA, ni authentification, ni protections anti-bot. L'envoi réel est désactivé par défaut.

## Version

FEWURA PROSPECT V1.0.0
