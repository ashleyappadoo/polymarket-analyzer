"""
Polymarket Strategy Analyzer API
Backend FastAPI pour analyse de marchés Polymarket avec TimesFM
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List, Dict
import json
from datetime import datetime, timedelta

app = FastAPI(title="Polymarket Strategy Analyzer API")

# CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier le domaine exact
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

class MarketAnalysis(BaseModel):
    market_info: Dict
    timesfm_analysis: Dict
    strategy: Dict
    recommendation: str

@app.get("/")
async def root():
    """Endpoint de santé"""
    return {
        "status": "healthy",
        "service": "Polymarket Strategy Analyzer API",
        "version": "1.0.0"
    }

@app.post("/api/analyze", response_model=MarketAnalysis)
async def analyze_market(request: AnalyzeRequest):
    """
    Analyse un marché Polymarket et retourne une stratégie
    
    Args:
        request: URL du marché Polymarket
        
    Returns:
        Analyse complète avec stratégie de trading
    """
    try:
        # 1. Extraire le token ID de l'URL
        token_id = extract_token_id(request.url)
        if not token_id:
            raise HTTPException(status_code=400, detail="URL invalide. Format attendu: https://polymarket.com/event/xxx#yyy")
        
        # 2. Récupérer les données du marché
        market_data = await fetch_market_data(token_id)
        
        # 3. Récupérer l'historique des prix
        price_history = await fetch_price_history(token_id)
        
        # 4. Analyser avec TimesFM
        timesfm_analysis = await analyze_with_timesfm(price_history)
        
        # 5. Générer la stratégie
        strategy = generate_strategy(market_data, timesfm_analysis)
        
        # 6. Déterminer la recommandation
        recommendation = determine_recommendation(timesfm_analysis, strategy)
        
        return MarketAnalysis(
            market_info=market_data,
            timesfm_analysis=timesfm_analysis,
            strategy=strategy,
            recommendation=recommendation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

def extract_token_id(url: str) -> Optional[str]:
    """Extrait le token ID de l'URL Polymarket"""
    # Format: https://polymarket.com/event/xxx#TOKEN_ID
    if "#" in url:
        return url.split("#")[-1]
    return None

async def fetch_market_data(token_id: str) -> Dict:
    """Récupère les données du marché depuis l'API Polymarket"""
    async with httpx.AsyncClient() as client:
        try:
            # Récupérer les données du token depuis gamma-api
            response = await client.get(
                f"{GAMMA_API_BASE}/markets",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": 100
                },
                timeout=10.0
            )
            response.raise_for_status()
            markets = response.json()
            
            # Trouver le marché correspondant au token_id
            for market in markets:
                # Le token_id correspond au conditionId ou à un des tokens
                if (market.get('conditionId') == token_id or 
                    any(token_id in str(token) for token in market.get('tokens', []))):
                    
                    # Extraire les informations pertinentes
                    return {
                        "question": market.get('question', 'Unknown'),
                        "description": market.get('description', ''),
                        "option_name": market.get('outcomes', ['Unknown'])[0] if market.get('outcomes') else 'Unknown',
                        "current_price": float(market.get('outcomePrices', [0.5])[0]),
                        "volume_24h": float(market.get('volume24hr', 0)),
                        "liquidity": float(market.get('liquidity', 0)),
                        "spread": float(market.get('spread', 0)),
                        "end_date": market.get('endDate', ''),
                        "market_id": market.get('id', ''),
                        "condition_id": market.get('conditionId', ''),
                    }
            
            # Si aucun marché trouvé, retourner des données par défaut
            raise HTTPException(status_code=404, detail="Marché non trouvé")
            
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Erreur API Polymarket: {str(e)}")

async def fetch_price_history(token_id: str) -> List[Dict]:
    """Récupère l'historique des prix depuis CLOB API"""
    async with httpx.AsyncClient() as client:
        try:
            # Calculer timestamps (7 derniers jours)
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
                
                # Convertir au format attendu
                return [
                    {
                        "timestamp": int(point.get('t', 0)) * 1000,
                        "price": float(point.get('p', 0.5))
                    }
                    for point in history
                ]
            else:
                # Fallback: générer un historique synthétique
                return generate_synthetic_history()
                
        except Exception as e:
            # En cas d'erreur, générer un historique synthétique
            return generate_synthetic_history()

def generate_synthetic_history() -> List[Dict]:
    """Génère un historique de prix synthétique pour les tests"""
    import random
    history = []
    base_price = 0.5
    now = datetime.now()
    
    for i in range(168):  # 7 jours * 24 heures
        base_price += random.uniform(-0.02, 0.02)
        base_price = max(0.1, min(0.9, base_price))
        
        history.append({
            "timestamp": int((now - timedelta(hours=168-i)).timestamp() * 1000),
            "price": round(base_price, 3)
        })
    
    return history

async def analyze_with_timesfm(price_history: List[Dict]) -> Dict:
    """Analyse l'historique avec TimesFM"""
    async with httpx.AsyncClient() as client:
        try:
            # Extraire les prix
            prices = [point["price"] for point in price_history]
            
            if len(prices) < 10:
                raise ValueError("Historique insuffisant")
            
            # Appeler TimesFM API
            response = await client.post(
                TIMESFM_API_URL,
                json={
                    "prices": prices,
                    "horizon": 24
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                timesfm_data = response.json()
                
                # Calculer les métriques
                mean = sum(prices) / len(prices)
                variance = sum((p - mean) ** 2 for p in prices) / len(prices)
                volatility = (variance ** 0.5) / mean * 100
                
                stability = max(0, min(100, 100 - volatility * 10))
                
                # Déterminer la tendance
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
                    "forecast": timesfm_data.get("forecast", []),
                    "tradeable": volatility < 10 and stability > 60
                }
            else:
                # Fallback: analyse basique
                return basic_analysis(prices)
                
        except Exception as e:
            # Fallback en cas d'erreur
            return basic_analysis([point["price"] for point in price_history])

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

def generate_strategy(market_data: Dict, timesfm_analysis: Dict) -> Dict:
    """Génère une stratégie de trading basée sur l'analyse"""
    current_price = market_data["current_price"]
    volatility = timesfm_analysis["volatility"]
    stability = timesfm_analysis["stability"]
    trend = timesfm_analysis["trend"]
    
    # Montant suggéré basé sur la volatilité
    if volatility < 5:
        suggested_amount = "$50-100"
        amount_min = 50
        amount_max = 100
    elif volatility < 8:
        suggested_amount = "$30-50"
        amount_min = 30
        amount_max = 50
    else:
        suggested_amount = "$10-30"
        amount_min = 10
        amount_max = 30
    
    # Prix d'entrée (légèrement en dessous du prix actuel)
    entry_price_min = round(current_price * 0.95, 3)
    entry_price_max = round(current_price * 1.02, 3)
    
    # Prix de sortie cible (20% de gain)
    exit_price = round(current_price * 1.20, 3)
    
    # Stop-loss (15% de perte)
    stop_loss = round(current_price * 0.85, 3)
    
    # ROI potentiel
    if trend == "Haussière" and stability > 70:
        roi_potential = "+15-25%"
    elif trend == "Haussière":
        roi_potential = "+10-20%"
    else:
        roi_potential = "+5-15%"
    
    # Niveau de risque
    if volatility < 5:
        risk_level = "Faible ✅"
    elif volatility < 8:
        risk_level = "Moyen ⚠️"
    else:
        risk_level = "Élevé ❌"
    
    return {
        "suggested_amount": suggested_amount,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "entry_price_min": entry_price_min,
        "entry_price_max": entry_price_max,
        "exit_price": exit_price,
        "stop_loss": stop_loss,
        "roi_potential": roi_potential,
        "risk_level": risk_level
    }

def determine_recommendation(timesfm_analysis: Dict, strategy: Dict) -> str:
    """Détermine la recommandation finale"""
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

# Pour Vercel, le handler doit être exposé
handler = app
