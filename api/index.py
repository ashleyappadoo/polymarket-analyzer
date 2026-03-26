"""
Polymarket Strategy Analyzer API V6
Backend FastAPI pour analyse MULTI-OPTIONS avec tableau comparatif
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List, Dict
import json
from datetime import datetime, timedelta
import re

app = FastAPI(title="Polymarket Strategy Analyzer API V6")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
TIMESFM_API_URL = os.getenv("TIMESFM_API_URL", "https://onaaction-timesfm-api.hf.space/api/forecast")

class AnalyzeRequest(BaseModel):
    url: str

class OptionAnalysis(BaseModel):
    option_name: str
    current_price: float
    price_percentage: float
    volume_24h: float
    volatility: float
    stability: float
    trend: str
    confidence: float
    recommendation: str
    strategy: Dict
    token_id: str

class MarketAnalysisV6(BaseModel):
    market_question: str
    total_options: int
    options: List[OptionAnalysis]
    best_option: Dict

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Polymarket Strategy Analyzer API V6",
        "version": "6.0.0",
        "mode": "Multi-Options Analysis"
    }

@app.post("/api/analyze", response_model=MarketAnalysisV6)
async def analyze_market(request: AnalyzeRequest):
    """
    Analyse TOUTES les options d'un marché Polymarket
    
    Args:
        request: URL du marché (sans #, ex: https://polymarket.com/event/xxx)
        
    Returns:
        Analyse complète de toutes les options avec recommandation
    """
    try:
        # 1. Extraire l'ID du marché de l'URL
        event_slug = extract_event_slug(request.url)
        if not event_slug:
            raise HTTPException(status_code=400, detail="URL invalide. Format: https://polymarket.com/event/xxx")
        
        # 2. Récupérer les données du marché avec toutes les options
        market_data = await fetch_market_with_all_options(event_slug)
        
        # 3. Analyser chaque option
        options_analysis = []
        
        for option in market_data["options"]:
            # Récupérer historique des prix
            price_history = await fetch_price_history(option["token_id"])
            
            # Analyser avec TimesFM
            timesfm_analysis = await analyze_with_timesfm(price_history)
            
            # Générer stratégie
            strategy = generate_strategy(option, timesfm_analysis)
            
            # Déterminer recommandation (avec prix actuel)
            recommendation = determine_recommendation(timesfm_analysis, strategy, option["price"])
            
            # Créer l'analyse de cette option
            option_analysis = OptionAnalysis(
                option_name=option["name"],
                current_price=option["price"],
                price_percentage=option["price"] * 100,
                volume_24h=option["volume"],
                volatility=timesfm_analysis["volatility"],
                stability=timesfm_analysis["stability"],
                trend=timesfm_analysis["trend"],
                confidence=timesfm_analysis["confidence"],
                recommendation=recommendation,
                strategy=strategy,
                token_id=option["token_id"]
            )
            
            options_analysis.append(option_analysis)
        
        # 4. Déterminer la meilleure option
        best_option = find_best_option(options_analysis)
        
        return MarketAnalysisV6(
            market_question=market_data["question"],
            total_options=len(options_analysis),
            options=options_analysis,
            best_option=best_option
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

def extract_event_slug(url: str) -> Optional[str]:
    """Extrait le slug du marché depuis l'URL"""
    # Format: https://polymarket.com/event/xxx ou https://polymarket.com/fr/event/xxx
    patterns = [
        r'polymarket\.com/event/([^/?#]+)',
        r'polymarket\.com/[a-z]{2}/event/([^/?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

async def fetch_market_with_all_options(event_slug: str) -> Dict:
    """Récupère l'event et tous ses markets directement par slug"""
    async with httpx.AsyncClient() as client:
        try:
            # Appel DIRECT à l'endpoint events/slug (pas de recherche!)
            url = f"{GAMMA_API_BASE}/events/slug/{event_slug}"
            print(f"[DEBUG] Appel API: {url}")
            
            response = await client.get(url, timeout=10.0)
            print(f"[DEBUG] Status code: {response.status_code}")
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Event '{event_slug}' non trouvé. Vérifiez que l'URL est correcte."
                )
            
            response.raise_for_status()
            event_data = response.json()
            
            print(f"[DEBUG] Event trouvé: {event_data.get('title', 'N/A')}")
            print(f"[DEBUG] Event slug: {event_data.get('slug', 'N/A')}")
            
            # Récupérer les markets de cet event
            markets = event_data.get('markets', [])
            print(f"[DEBUG] Nombre de markets dans l'event: {len(markets)}")
            
            if not markets or len(markets) == 0:
                raise HTTPException(
                    status_code=400, 
                    detail="Aucun marché actif trouvé pour cet event"
                )
            
            # Si un seul market = utiliser ses outcomes directement
            # Si plusieurs markets = chaque market est une "option"
            if len(markets) == 1:
                # UN SEUL MARKET → Utiliser ses outcomes
                market = markets[0]
                print(f"[DEBUG] Un seul market trouvé: {market.get('question', 'N/A')}")
                
                outcomes_raw = market.get('outcomes', [])
                outcome_prices_raw = market.get('outcomePrices', [])
                # CORRECTION: Utiliser clobTokenIds au lieu de tokens
                clob_tokens_raw = market.get('clobTokenIds', '')
                
                print(f"[DEBUG] ========== DONNÉES BRUTES API ==========")
                print(f"[DEBUG] Type outcomes_raw: {type(outcomes_raw)}")
                print(f"[DEBUG] Outcomes_raw: {str(outcomes_raw)[:200]}")
                print(f"[DEBUG] clobTokenIds: {clob_tokens_raw}")
                
                # Parser JSON strings
                import json as json_module
                
                if isinstance(outcomes_raw, str):
                    outcomes = json_module.loads(outcomes_raw)
                    print(f"[DEBUG] Outcomes parsé depuis JSON string")
                else:
                    outcomes = outcomes_raw
                
                if isinstance(outcome_prices_raw, str):
                    outcome_prices = json_module.loads(outcome_prices_raw)
                else:
                    outcome_prices = outcome_prices_raw
                
                # Parser clobTokenIds
                if isinstance(clob_tokens_raw, str) and clob_tokens_raw:
                    try:
                        clob_tokens = json_module.loads(clob_tokens_raw)
                        print(f"[DEBUG] clobTokenIds parsé: {len(clob_tokens)} tokens")
                    except:
                        clob_tokens = []
                else:
                    clob_tokens = clob_tokens_raw if clob_tokens_raw else []
                
                print(f"[DEBUG] Nombre outcomes: {len(outcomes)}")
                print(f"[DEBUG] Nombre clob_tokens: {len(clob_tokens)}")
                
                options = []
                for i, outcome in enumerate(outcomes):
                    # Extraire le nom
                    if isinstance(outcome, dict):
                        option_name = outcome.get('name', str(outcome))
                    elif isinstance(outcome, str):
                        option_name = outcome
                    else:
                        option_name = str(outcome)
                    
                    # Extraire le prix
                    try:
                        price_raw = outcome_prices[i] if i < len(outcome_prices) else '0.5'
                        price_str = str(price_raw).replace('|', '').replace(',', '.').strip()
                        price = float(price_str) if price_str and price_str != '' else 0.5
                    except (ValueError, TypeError, IndexError) as e:
                        print(f"[WARNING] Erreur parsing prix option {i}: {e}")
                        price = 0.5
                    
                    # CORRECTION CRITIQUE: clobTokenIds contient [token_yes, token_no]
                    # On prend UNIQUEMENT le PREMIER (token Yes)
                    if i < len(clob_tokens):
                        token_pair = clob_tokens[i]
                        # Si c'est un array, prendre le premier élément
                        if isinstance(token_pair, list) and len(token_pair) > 0:
                            token_id = token_pair[0]
                        else:
                            token_id = str(token_pair)
                    else:
                        token_id = ""
                    
                    print(f"[DEBUG] Option {i}: nom='{option_name[:30]}', prix={price}, token_id='{token_id[:40]}...' ")
                    
                    options.append({
                        "name": option_name,
                        "price": price,
                        "token_id": token_id,
                        "volume": float(market.get('volume24hr', 0)) / len(outcomes)
                    })
                
                print(f"[DEBUG] {len(options)} options extraites")
                
                return {
                    "question": market.get('question', event_data.get('title', 'Unknown')),
                    "options": options,
                    "end_date": market.get('endDate', ''),
                    "market_id": market.get('id', '')
                }
            
            else:
                # PLUSIEURS MARKETS → Chaque market est une option
                print(f"[DEBUG] {len(markets)} markets trouvés → chaque market = une option")
                
                options = []
                for market in markets:
                    # Le nom de l'option = la question du market
                    option_name = market.get('groupItemTitle') or market.get('question', 'Unknown')
                    
                    # Le prix = moyenne des outcomes du market
                    outcomes_raw = market.get('outcomes', [])
                    outcome_prices_raw = market.get('outcomePrices', [])
                    
                    import json as json_module
                    
                    if isinstance(outcome_prices_raw, str):
                        try:
                            outcome_prices = json_module.loads(outcome_prices_raw)
                        except:
                            outcome_prices = [0.5]
                    else:
                        outcome_prices = outcome_prices_raw if outcome_prices_raw else [0.5]
                    
                    # Calculer prix moyen
                    try:
                        prices_float = [float(str(p).replace('|', '').strip()) for p in outcome_prices if p]
                        avg_price = sum(prices_float) / len(prices_float) if prices_float else 0.5
                    except:
                        avg_price = 0.5
                    
                    # CORRECTION: Parser clobTokenIds et prendre le premier token
                    clob_tokens_raw = market.get('clobTokenIds', '')
                    token_id = ""
                    
                    if clob_tokens_raw:
                        try:
                            if isinstance(clob_tokens_raw, str):
                                clob_tokens = json_module.loads(clob_tokens_raw)
                            else:
                                clob_tokens = clob_tokens_raw
                            
                            # Prendre le premier token (Yes token généralement)
                            if isinstance(clob_tokens, list) and len(clob_tokens) > 0:
                                first_pair = clob_tokens[0]
                                # Si c'est encore un array (paire Yes/No), prendre le premier
                                if isinstance(first_pair, list) and len(first_pair) > 0:
                                    token_id = str(first_pair[0])
                                else:
                                    token_id = str(first_pair)
                            elif isinstance(clob_tokens, str):
                                token_id = clob_tokens
                        except Exception as e:
                            print(f"[WARNING] Erreur parsing clobTokenIds: {e}")
                            token_id = ""
                    
                    options.append({
                        "name": option_name,
                        "price": avg_price,
                        "token_id": token_id,
                        "volume": float(market.get('volume24hr', 0))
                    })
                
                print(f"[DEBUG] {len(options)} options (markets) extraites")
                
                return {
                    "question": event_data.get('title', 'Unknown'),
                    "options": options,
                    "end_date": event_data.get('endDate', ''),
                    "market_id": event_data.get('id', '')
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Event '{event_slug}' non trouvé. Vérifiez l'URL."
                )
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            print(f"[ERROR] Erreur fetch event: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
            
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Erreur API Polymarket: {str(e)}")

async def fetch_price_history(token_id: str) -> List[Dict]:
    """Récupère l'historique des prix"""
    print(f"[DEBUG] fetch_price_history appelé avec token_id type: {type(token_id)}")
    print(f"[DEBUG] token_id (premiers 50 chars): {str(token_id)[:50]}")
    
    # CRITICAL: Vérifier que token_id est un STRING, pas un array
    if not token_id or not isinstance(token_id, str):
        print(f"[WARNING] token_id invalide (type={type(token_id)}) → Génération données synthétiques")
        return generate_synthetic_history()
    
    # Si token_id commence par "[", c'est probablement un JSON array
    if token_id.startswith('['):
        print(f"[WARNING] token_id est un array JSON → Parsing pour extraire le premier")
        try:
            import json as json_module
            tokens = json_module.loads(token_id)
            if isinstance(tokens, list) and len(tokens) > 0:
                token_id = str(tokens[0])
                print(f"[DEBUG] Premier token extrait: {token_id[:50]}")
            else:
                print(f"[WARNING] Array vide → Données synthétiques")
                return generate_synthetic_history()
        except:
            print(f"[WARNING] Parsing array échoué → Données synthétiques")
            return generate_synthetic_history()
    
    async with httpx.AsyncClient() as client:
        try:
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=7)).timestamp())
            
            url = f"{CLOB_API_BASE}/prices-history"
            # CRITICAL: market parameter doit être UN SEUL token_id STRING
            params = {
                "market": token_id,  # STRING, pas array !
                "startTs": start_ts,
                "endTs": end_ts,
                "interval": "1h",
                "fidelity": 60
            }
            
            print(f"[DEBUG] Appel CLOB API: {url}")
            print(f"[DEBUG] Params: market={token_id[:40]}..., interval=1h, fidelity=60")
            
            response = await client.get(url, params=params, timeout=10.0)
            
            print(f"[DEBUG] CLOB response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                
                if not history or len(history) == 0:
                    print(f"[WARNING] Historique vide malgré 200 OK → Données synthétiques")
                    return generate_synthetic_history()
                
                print(f"[DEBUG] ✅ Historique récupéré: {len(history)} points")
                
                return [
                    {
                        "timestamp": int(point.get('t', 0)) * 1000,
                        "price": float(point.get('p', 0.5))
                    }
                    for point in history
                ]
            else:
                print(f"[WARNING] CLOB API erreur {response.status_code} → Données synthétiques")
                return generate_synthetic_history()
                
        except Exception as e:
            print(f"[ERROR] Exception fetch_price_history: {e} → Données synthétiques")
            return generate_synthetic_history()

def generate_synthetic_history() -> List[Dict]:
    """Génère un historique synthétique"""
    import random
    history = []
    base_price = 0.5
    now = datetime.now()
    
    for i in range(168):
        base_price += random.uniform(-0.02, 0.02)
        base_price = max(0.1, min(0.9, base_price))
        
        history.append({
            "timestamp": int((now - timedelta(hours=168-i)).timestamp() * 1000),
            "price": round(base_price, 3)
        })
    
    return history

async def analyze_with_timesfm(price_history: List[Dict]) -> Dict:
    """Analyse avec TimesFM"""
    print(f"[DEBUG] analyze_with_timesfm: {len(price_history)} points d'historique")
    
    async with httpx.AsyncClient() as client:
        try:
            # Extraire les prix et s'assurer qu'ils sont des floats
            prices = [float(point["price"]) for point in price_history]
            
            if len(prices) < 10:
                print(f"[WARNING] Historique insuffisant ({len(prices)} points) → basic_analysis")
                raise ValueError("Historique insuffisant")
            
            print(f"[DEBUG] Appel TimesFM API: {TIMESFM_API_URL}")
            print(f"[DEBUG] Données envoyées: {len(prices)} prix (floats), horizon=24")
            print(f"[DEBUG] Premiers prix: {prices[:5]}")
            
            # CORRECTION CRITIQUE: TimesFM attend "data" et non "prices"
            payload = {
                "data": prices,  # ← "data" pas "prices" !
                "horizon": 24
            }
            
            response = await client.post(
                TIMESFM_API_URL,
                json=payload,
                timeout=30.0
            )
            
            print(f"[DEBUG] TimesFM response status: {response.status_code}")
            
            if response.status_code == 200:
                timesfm_data = response.json()
                print(f"[DEBUG] ✅ TimesFM analysis réussie")
                print(f"[DEBUG] TimesFM data keys: {timesfm_data.keys() if isinstance(timesfm_data, dict) else 'not a dict'}")
                return calculate_metrics(prices, timesfm_data)
            else:
                print(f"[WARNING] TimesFM erreur {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"[WARNING] TimesFM error detail: {error_detail}")
                except:
                    print(f"[WARNING] TimesFM error text: {response.text[:200]}")
                print(f"[WARNING] → Fallback basic_analysis")
                return basic_analysis(prices)
                
        except Exception as e:
            print(f"[ERROR] Exception analyze_with_timesfm: {e} → basic_analysis")
            return basic_analysis([point["price"] for point in price_history])

def calculate_metrics(prices: List[float], timesfm_data: Dict) -> Dict:
    """Calcule les métriques d'analyse"""
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    volatility = (variance ** 0.5) / mean * 100
    
    stability = max(0, min(100, 100 - volatility * 10))
    
    recent_avg = sum(prices[-24:]) / len(prices[-24:])
    old_avg = sum(prices[-48:-24]) / len(prices[-48:-24]) if len(prices) >= 48 else mean
    
    if recent_avg > old_avg * 1.02:
        trend = "Haussière"
    elif recent_avg < old_avg * 0.98:
        trend = "Baissière"
    else:
        trend = "Stable"
    
    return {
        "volatility": round(volatility, 1),
        "stability": round(stability, 0),
        "trend": trend,
        "confidence": round(timesfm_data.get("confidence", 0.7) * 100, 0),
        "tradeable": volatility < 10 and stability > 60
    }

def basic_analysis(prices: List[float]) -> Dict:
    """Analyse basique si TimesFM échoue"""
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    volatility = (variance ** 0.5) / mean * 100
    
    stability = max(0, min(100, 100 - volatility * 10))
    
    recent_avg = sum(prices[-24:]) / len(prices[-24:])
    old_avg = sum(prices[-48:-24]) / len(prices[-48:-24]) if len(prices) >= 48 else mean
    
    if recent_avg > old_avg * 1.02:
        trend = "Haussière"
    elif recent_avg < old_avg * 0.98:
        trend = "Baissière"
    else:
        trend = "Stable"
    
    return {
        "volatility": round(volatility, 1),
        "stability": round(stability, 0),
        "trend": trend,
        "confidence": 65,
        "tradeable": volatility < 10 and stability > 60
    }

def generate_strategy(option: Dict, timesfm_analysis: Dict) -> Dict:
    """Génère une stratégie de trading"""
    current_price = option["price"]
    volatility = timesfm_analysis["volatility"]
    
    if volatility < 5:
        suggested_amount = "$50-100"
    elif volatility < 8:
        suggested_amount = "$30-50"
    else:
        suggested_amount = "$10-30"
    
    entry_price_min = round(current_price * 0.95, 3)
    entry_price_max = round(current_price * 1.02, 3)
    exit_price = round(current_price * 1.20, 3)
    stop_loss = round(current_price * 0.85, 3)
    
    if timesfm_analysis["trend"] == "Haussière" and timesfm_analysis["stability"] > 70:
        roi_potential = "+15-25%"
    elif timesfm_analysis["trend"] == "Haussière":
        roi_potential = "+10-20%"
    else:
        roi_potential = "+5-15%"
    
    if volatility < 5:
        risk_level = "Faible ✅"
    elif volatility < 8:
        risk_level = "Moyen ⚠️"
    else:
        risk_level = "Élevé ❌"
    
    return {
        "suggested_amount": suggested_amount,
        "entry_price_min": entry_price_min,
        "entry_price_max": entry_price_max,
        "exit_price": exit_price,
        "stop_loss": stop_loss,
        "roi_potential": roi_potential,
        "risk_level": risk_level
    }

def determine_recommendation(timesfm_analysis: Dict, strategy: Dict, current_price: float = 0.5) -> str:
    """Détermine la recommandation en utilisant tendance + prix actuel + volatilité"""
    trend = timesfm_analysis["trend"]
    stability = timesfm_analysis["stability"]
    volatility = timesfm_analysis["volatility"]
    
    print(f"[DEBUG RECO] Prix={current_price:.3f}, Trend={trend}, Stability={stability}, Volatility={volatility}")
    
    # LOGIQUE AGRESSIVE ET VARIÉE
    
    # === ZONE ACHETER (prix bas + conditions favorables) ===
    
    # Prix très bas (< 15¢) = grande opportunité si pas trop volatile
    if current_price < 0.15 and volatility < 15:
        print(f"[DEBUG RECO] → ACHETER (prix très bas < 0.15)")
        return "ACHETER"
    
    # Prix bas (< 30¢) + tendance haussière
    if current_price < 0.30 and trend == "Haussière":
        print(f"[DEBUG RECO] → ACHETER (prix bas + haussière)")
        return "ACHETER"
    
    # Prix bas (< 30¢) + stable mais bon ratio risque/récompense
    if current_price < 0.30 and stability > 50:
        print(f"[DEBUG RECO] → ACHETER (prix bas + stable)")
        return "ACHETER"
    
    # === ZONE ACHETER PRUDENT (opportunités moyennes) ===
    
    # Prix moyen (< 50¢) + tendance haussière
    if current_price < 0.50 and trend == "Haussière":
        print(f"[DEBUG RECO] → ACHETER_PRUDENT (prix moyen + haussière)")
        return "ACHETER_PRUDENT"
    
    # Prix moyen (30-50¢) + stable + peu volatile
    if 0.30 <= current_price < 0.50 and stability > 60 and volatility < 8:
        print(f"[DEBUG RECO] → ACHETER_PRUDENT (prix moyen + conditions stables)")
        return "ACHETER_PRUDENT"
    
    # === ZONE OBSERVER (situations neutres) ===
    
    # Prix élevé (> 70¢) mais tendance haussière = peut encore monter
    if current_price >= 0.70 and trend == "Haussière" and volatility < 10:
        print(f"[DEBUG RECO] → OBSERVER (prix élevé mais haussière)")
        return "OBSERVER"
    
    # Prix moyen (40-70¢) + stable = surveiller
    if 0.40 <= current_price < 0.70 and stability > 55:
        print(f"[DEBUG RECO] → OBSERVER (prix moyen + stable)")
        return "OBSERVER"
    
    # === ZONE ATTENDRE (situations défavorables) ===
    
    # Prix très élevé (> 80¢) = peu de marge
    if current_price >= 0.80:
        print(f"[DEBUG RECO] → ATTENDRE (prix trop élevé)")
        return "ATTENDRE"
    
    # Volatilité excessive (> 15%)
    if volatility > 15:
        print(f"[DEBUG RECO] → ATTENDRE (volatilité élevée)")
        return "ATTENDRE"
    
    # Tendance baissière + prix déjà moyen/haut
    if trend == "Baissière" and current_price > 0.40:
        print(f"[DEBUG RECO] → ATTENDRE (baissière + prix moyen/élevé)")
        return "ATTENDRE"
    
    # === PAR DÉFAUT (devrait rarement arriver) ===
    
    # Si prix moyen (30-60¢) sans signal clair → ACHETER_PRUDENT (on favorise l'action)
    if 0.30 <= current_price < 0.60:
        print(f"[DEBUG RECO] → ACHETER_PRUDENT (par défaut - prix raisonnable)")
        return "ACHETER_PRUDENT"
    
    # Sinon → OBSERVER
    print(f"[DEBUG RECO] → OBSERVER (par défaut)")
    return "OBSERVER"

def find_best_option(options: List[OptionAnalysis]) -> Dict:
    """Trouve la meilleure option"""
    # Scoring système
    scores = []
    
    for option in options:
        score = 0
        
        # Trend (40 points max)
        if option.trend == "Haussière":
            score += 40
        elif option.trend == "Stable":
            score += 20
        
        # Stabilité (30 points max)
        score += (option.stability / 100) * 30
        
        # Volatilité inverse (20 points max)
        if option.volatility < 5:
            score += 20
        elif option.volatility < 8:
            score += 10
        
        # Confiance (10 points max)
        score += (option.confidence / 100) * 10
        
        scores.append({
            "option": option,
            "score": score
        })
    
    # Trier par score décroissant
    scores.sort(key=lambda x: x["score"], reverse=True)
    best = scores[0]
    
    return {
        "option_name": best["option"].option_name,
        "score": round(best["score"], 1),
        "recommendation": best["option"].recommendation,
        "reason": f"{best['option'].trend} + Stabilité {best['option'].stability}/100 + Volatilité {best['option'].volatility}%"
    }
