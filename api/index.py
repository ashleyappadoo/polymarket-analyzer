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
            
            # Déterminer recommandation
            recommendation = determine_recommendation(timesfm_analysis, strategy)
            
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
    """Récupère le marché et toutes ses options"""
    async with httpx.AsyncClient() as client:
        try:
            # Rechercher le marché via l'API
            response = await client.get(
                f"{GAMMA_API_BASE}/markets",
                params={"active": "true", "closed": "false", "limit": 100},
                timeout=10.0
            )
            response.raise_for_status()
            markets = response.json()
            
            # Trouver le marché correspondant au slug
            target_market = None
            for market in markets:
                # Comparer avec le slug de la question
                market_slug = market.get('slug', '')
                if event_slug in market_slug or market_slug in event_slug:
                    target_market = market
                    break
            
            if not target_market:
                raise HTTPException(status_code=404, detail="Marché non trouvé")
            
            # Extraire toutes les options
            outcomes = target_market.get('outcomes', [])
            outcome_prices = target_market.get('outcomePrices', [])
            tokens = target_market.get('tokens', [])
            
            if not outcomes or len(outcomes) == 0:
                raise HTTPException(status_code=400, detail="Aucune option trouvée pour ce marché")
            
            options = []
            for i, outcome in enumerate(outcomes):
                price = float(outcome_prices[i]) if i < len(outcome_prices) else 0.5
                token_id = tokens[i] if i < len(tokens) else ""
                
                options.append({
                    "name": outcome,
                    "price": price,
                    "token_id": token_id,
                    "volume": float(target_market.get('volume24hr', 0)) / len(outcomes)
                })
            
            return {
                "question": target_market.get('question', 'Unknown'),
                "options": options,
                "end_date": target_market.get('endDate', ''),
                "market_id": target_market.get('id', '')
            }
            
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Erreur API Polymarket: {str(e)}")

async def fetch_price_history(token_id: str) -> List[Dict]:
    """Récupère l'historique des prix"""
    async with httpx.AsyncClient() as client:
        try:
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=7)).timestamp())
            
            response = await client.get(
                f"{CLOB_API_BASE}/prices-history",
                params={
                    "market": token_id,
                    "startTs": start_ts,
                    "endTs": end_ts,
                    "interval": "1h",
                    "fidelity": 60
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                
                return [
                    {
                        "timestamp": int(point.get('t', 0)) * 1000,
                        "price": float(point.get('p', 0.5))
                    }
                    for point in history
                ]
            else:
                return generate_synthetic_history()
                
        except Exception:
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
    async with httpx.AsyncClient() as client:
        try:
            prices = [point["price"] for point in price_history]
            
            if len(prices) < 10:
                raise ValueError("Historique insuffisant")
            
            response = await client.post(
                TIMESFM_API_URL,
                json={"prices": prices, "horizon": 24},
                timeout=30.0
            )
            
            if response.status_code == 200:
                timesfm_data = response.json()
                return calculate_metrics(prices, timesfm_data)
            else:
                return basic_analysis(prices)
                
        except Exception:
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

def determine_recommendation(timesfm_analysis: Dict, strategy: Dict) -> str:
    """Détermine la recommandation"""
    trend = timesfm_analysis["trend"]
    stability = timesfm_analysis["stability"]
    volatility = timesfm_analysis["volatility"]
    
    if trend == "Haussière" and stability > 70 and volatility < 6:
        return "ACHETER"
    elif trend == "Haussière" and stability > 60:
        return "ACHETER_PRUDENT"
    elif volatility > 8 or stability < 50:
        return "ATTENDRE"
    else:
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
