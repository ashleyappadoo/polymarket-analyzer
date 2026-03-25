import { useState } from 'react';
import Head from 'next/head';
import styles from '../styles/Home.module.css';

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const analyzeMarket = async () => {
    if (!url) {
      setError('Veuillez entrer une URL Polymarket');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur lors de l\'analyse');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationClass = (recommendation) => {
    if (recommendation === 'ACHETER') return styles.buy;
    if (recommendation === 'ACHETER_PRUDENT') return styles.buy;
    if (recommendation === 'ATTENDRE') return styles.sell;
    return styles.hold;
  };

  const getRecommendationText = (recommendation) => {
    switch (recommendation) {
      case 'ACHETER':
        return {
          title: '🟢 ACHETER',
          text: 'Excellente opportunité ! Tous les indicateurs sont au vert. Tendance haussière confirmée avec bonne stabilité.',
        };
      case 'ACHETER_PRUDENT':
        return {
          title: '🟡 ACHETER PRUDEMMENT',
          text: 'Opportunité favorable mais avec prudence. Tendance positive mais volatilité modérée. Réduisez le montant investi.',
        };
      case 'ATTENDRE':
        return {
          title: '🔴 ATTENDRE',
          text: 'Marché trop volatil ou tendance défavorable. Attendez de meilleures conditions avant d\'entrer en position.',
        };
      default:
        return {
          title: '🔵 OBSERVER',
          text: 'Marché stable sans signal clair. Surveillez l\'évolution avant de prendre une décision.',
        };
    }
  };

  const getMetricClass = (value, metric) => {
    if (metric === 'volatility') {
      if (value < 5) return styles.good;
      if (value < 8) return styles.warning;
      return styles.bad;
    }
    if (metric === 'stability') {
      if (value > 70) return styles.good;
      if (value > 50) return styles.warning;
      return styles.bad;
    }
    if (metric === 'trend') {
      if (value === 'Haussière') return styles.good;
      if (value === 'Baissière') return styles.bad;
      return styles.warning;
    }
    if (metric === 'confidence') {
      if (value > 70) return styles.good;
      if (value > 50) return styles.warning;
      return styles.bad;
    }
    return '';
  };

  return (
    <div className={styles.container}>
      <Head>
        <title>Polymarket Strategy Analyzer</title>
        <meta name="description" content="Analysez n'importe quel marché Polymarket avec TimesFM" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className={styles.header}>
        <h1>🎯 Polymarket Strategy Analyzer</h1>
        <p>Analysez n'importe quel marché avec TimesFM et obtenez une stratégie de trading</p>
      </div>

      <div className={styles.content}>
        <div className={styles.inputGroup}>
          <label htmlFor="urlInput">URL du Marché Polymarket</label>
          <input
            id="urlInput"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://polymarket.com/event/2026-ncaa-tournament-winner#qb1jDUlo"
            onKeyPress={(e) => e.key === 'Enter' && analyzeMarket()}
          />
        </div>

        <button
          className={styles.button}
          onClick={analyzeMarket}
          disabled={loading}
        >
          {loading ? '⏳ Analyse en cours...' : '🚀 Analyser le Marché'}
        </button>

        {loading && (
          <div className={styles.loading}>
            <div className={styles.spinner}></div>
            <p>Récupération des données et prédiction TimesFM...</p>
          </div>
        )}

        {error && (
          <div className={styles.error}>
            <strong>Erreur:</strong> {error}
          </div>
        )}

        {result && (
          <div className={styles.result}>
            <div className={styles.marketInfo}>
              <h2>{result.market_info.question}</h2>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>📊 Option Analysée:</span>
                <span className={styles.infoValue}>{result.market_info.option_name}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>💰 Prix Actuel:</span>
                <span className={styles.infoValue}>${result.market_info.current_price.toFixed(3)}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>📈 Volume 24h:</span>
                <span className={styles.infoValue}>${(result.market_info.volume_24h / 1000).toFixed(0)}K</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>💵 Liquidité:</span>
                <span className={styles.infoValue}>${(result.market_info.liquidity / 1000).toFixed(0)}K</span>
              </div>
            </div>

            <div className={styles.timesfmAnalysis}>
              <h3>📊 Analyse TimesFM</h3>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Volatilité:</span>
                <span className={`${styles.metricValue} ${getMetricClass(result.timesfm_analysis.volatility, 'volatility')}`}>
                  {result.timesfm_analysis.volatility}%
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Stabilité:</span>
                <span className={`${styles.metricValue} ${getMetricClass(result.timesfm_analysis.stability, 'stability')}`}>
                  {result.timesfm_analysis.stability}/100
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Tendance:</span>
                <span className={`${styles.metricValue} ${getMetricClass(result.timesfm_analysis.trend, 'trend')}`}>
                  {result.timesfm_analysis.trend}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Confiance Prédiction:</span>
                <span className={`${styles.metricValue} ${getMetricClass(result.timesfm_analysis.confidence, 'confidence')}`}>
                  {result.timesfm_analysis.confidence}%
                </span>
              </div>
            </div>

            <div className={`${styles.recommendation} ${getRecommendationClass(result.recommendation)}`}>
              <h4>{getRecommendationText(result.recommendation).title}</h4>
              <p>{getRecommendationText(result.recommendation).text}</p>
            </div>

            <div className={styles.strategy}>
              <h3>💡 Stratégie de Trading</h3>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>💵 Montant Suggéré:</span>
                <span className={styles.strategyValue}>{result.strategy.suggested_amount}</span>
              </div>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>🎯 Prix d'Entrée:</span>
                <span className={styles.strategyValue}>
                  ${result.strategy.entry_price_min}-${result.strategy.entry_price_max}
                </span>
              </div>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>🎯 Prix de Sortie Cible:</span>
                <span className={styles.strategyValue}>${result.strategy.exit_price}+</span>
              </div>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>🛑 Stop-Loss:</span>
                <span className={styles.strategyValue}>${result.strategy.stop_loss}</span>
              </div>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>💰 ROI Potentiel:</span>
                <span className={styles.strategyValue}>{result.strategy.roi_potential}</span>
              </div>
              <div className={styles.strategyItem}>
                <span className={styles.strategyLabel}>⚠️ Niveau de Risque:</span>
                <span className={styles.strategyValue}>{result.strategy.risk_level}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <footer className={styles.footer}>
        <p>
          Made with ❤️ by ONA | Powered by TimesFM & Polymarket API
        </p>
      </footer>
    </div>
  );
}
