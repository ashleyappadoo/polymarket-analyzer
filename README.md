# 🎯 Polymarket Strategy Analyzer

Analysez n'importe quel marché Polymarket avec TimesFM et obtenez une stratégie de trading claire et précise.

![Polymarket Strategy Analyzer](https://img.shields.io/badge/Status-Production-green)
![Next.js](https://img.shields.io/badge/Next.js-14.0-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-teal)
![License](https://img.shields.io/badge/License-MIT-blue)

## ✨ Fonctionnalités

- ✅ **Analyse en Temps Réel** : Données live depuis l'API Polymarket
- ✅ **Prédictions TimesFM** : IA pour analyser les tendances
- ✅ **Stratégie Claire** : Montants, prix d'entrée/sortie, stop-loss
- ✅ **Interface Moderne** : Design responsive et élégant
- ✅ **100% Gratuit** : Hébergement gratuit sur Vercel

## 🚀 Demo

**Live Demo:** [https://votre-app.vercel.app](https://votre-app.vercel.app)

## 📸 Screenshots

![Screenshot 1](./docs/screenshot1.png)

## 🛠️ Technologies

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- CSS Modules

**Backend:**
- FastAPI (Python)
- HTTPX (Async HTTP client)
- Pydantic (Data validation)

**APIs:**
- Polymarket Gamma API
- Polymarket CLOB API
- TimesFM API (Hugging Face)

## 📦 Installation Locale

### Prérequis

- Node.js 18+ 
- Python 3.11+
- Git

### Étapes

1. **Cloner le repository**

```bash
git clone https://github.com/votre-username/polymarket-strategy-analyzer.git
cd polymarket-strategy-analyzer
```

2. **Installer les dépendances Frontend**

```bash
npm install
```

3. **Installer les dépendances Backend**

```bash
pip install -r api/requirements.txt
```

4. **Lancer en développement**

Terminal 1 (Frontend):
```bash
npm run dev
```

Terminal 2 (Backend):
```bash
uvicorn api.index:app --reload --port 8000
```

5. **Ouvrir dans le navigateur**

```
http://localhost:3000
```

## 🚀 Déploiement sur Vercel

### Méthode 1: Via GitHub (Recommandé)

1. **Créer un repository GitHub**

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/votre-username/polymarket-strategy-analyzer.git
git push -u origin main
```

2. **Connecter à Vercel**

- Allez sur [vercel.com](https://vercel.com)
- Cliquez sur "New Project"
- Importez votre repository GitHub
- Vercel détecte automatiquement Next.js et FastAPI
- Cliquez sur "Deploy"

3. **C'est tout !** ✅

Votre app sera disponible sur: `https://votre-app.vercel.app`

### Méthode 2: Via Vercel CLI

```bash
npm install -g vercel
vercel login
vercel
```

Suivez les instructions à l'écran.

## ⚙️ Configuration

### Variables d'Environnement

Créez un fichier `.env.local` à la racine:

```env
# TimesFM API (optionnel, URL par défaut fournie)
TIMESFM_API_URL=https://onaaction-timesfm-api.hf.space/api/forecast
```

Dans Vercel, ajoutez les variables via le dashboard:
Settings → Environment Variables

## 📖 Utilisation

1. **Trouver un marché sur Polymarket**
   - Allez sur [polymarket.com](https://polymarket.com)
   - Choisissez un marché qui vous intéresse
   - Cliquez sur une option spécifique

2. **Copier l'URL**
   ```
   https://polymarket.com/event/2026-ncaa-tournament-winner#qb1jDUlo
   ```
   ⚠️ Important: L'URL doit contenir le `#` suivi du token ID

3. **Analyser**
   - Collez l'URL dans le champ
   - Cliquez sur "Analyser le Marché"
   - Attendez 5-10 secondes

4. **Lire la stratégie**
   - Recommandation: ACHETER / ATTENDRE / OBSERVER
   - Prix d'entrée suggéré
   - Prix de sortie cible
   - Stop-loss
   - ROI potentiel
   - Niveau de risque

## 📊 Interprétation des Résultats

### Volatilité
- **< 5%** : Excellent ✅ (Marché stable)
- **5-8%** : Bon ⚠️ (Variations modérées)
- **> 8%** : Risqué ❌ (Marché volatil)

### Stabilité
- **> 70** : Excellent ✅ (Très prévisible)
- **50-70** : Correct ⚠️ (Modérément stable)
- **< 50** : Faible ❌ (Imprévisible)

### Tendance
- **Haussière** : Prix monte ✅
- **Stable** : Prix constant ⚠️
- **Baissière** : Prix baisse ❌

### Recommandations
- **🟢 ACHETER** : Tous les indicateurs au vert
- **🟡 ACHETER PRUDEMMENT** : Opportunité avec prudence
- **🔴 ATTENDRE** : Conditions défavorables
- **🔵 OBSERVER** : Marché stable sans signal

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐
│   Browser   │ ───▶ │  Next.js     │ ───▶ │  FastAPI   │
│  (Client)   │ ◀─── │  (Frontend)  │ ◀─── │  (Backend) │
└─────────────┘      └──────────────┘      └────────────┘
                                                   │
                                                   ▼
                                    ┌──────────────────────────┐
                                    │  External APIs:          │
                                    │  - Polymarket Gamma      │
                                    │  - Polymarket CLOB       │
                                    │  - TimesFM (Hugging Face)│
                                    └──────────────────────────┘
```

## 🔧 API Endpoints

### `POST /api/analyze`

Analyse un marché Polymarket.

**Request:**
```json
{
  "url": "https://polymarket.com/event/xxx#token_id"
}
```

**Response:**
```json
{
  "market_info": {
    "question": "Will Duke win NCAA 2026?",
    "current_price": 0.16,
    "volume_24h": 245000,
    "liquidity": 50000
  },
  "timesfm_analysis": {
    "volatility": 4.2,
    "stability": 82,
    "trend": "Haussière",
    "confidence": 73
  },
  "strategy": {
    "suggested_amount": "$50-100",
    "entry_price_min": 0.152,
    "entry_price_max": 0.168,
    "exit_price": 0.192,
    "stop_loss": 0.136,
    "roi_potential": "+15-25%",
    "risk_level": "Moyen ⚠️"
  },
  "recommendation": "ACHETER"
}
```

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📝 Roadmap

- [ ] Support multi-options (analyser toutes les options d'un marché)
- [ ] Historique des analyses
- [ ] Alertes par email/Telegram
- [ ] Mode comparaison (2+ marchés côte à côte)
- [ ] Export PDF des stratégies
- [ ] Backtesting des stratégies
- [ ] Portfolio tracker

## ⚠️ Disclaimer

Cet outil est fourni à titre informatif uniquement. Il ne constitue pas un conseil financier. 

- ❌ Ne garantit AUCUN profit
- ❌ Trading comporte des risques
- ✅ Faites vos propres recherches
- ✅ N'investissez que ce que vous pouvez perdre

## 📄 License

MIT License - voir [LICENSE](LICENSE)

## 👨‍💻 Auteur

**ONA**
- Website: [ona-action.fr](https://ona-action.fr)
- GitHub: [@votre-username](https://github.com/votre-username)
- Twitter: [@votre-handle](https://twitter.com/votre-handle)

## 🙏 Remerciements

- [Polymarket](https://polymarket.com) - Données de marché
- [TimesFM](https://huggingface.co/google/timesfm-1.0-200m) - Modèle de prédiction
- [Vercel](https://vercel.com) - Hébergement
- [Next.js](https://nextjs.org) - Framework React
- [FastAPI](https://fastapi.tiangolo.com) - Framework Python

---

Made with ❤️ by ONA
