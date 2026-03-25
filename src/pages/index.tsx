import { useState } from 'react';
import Head from 'next/head';
import styles from '../styles/Home.module.css';

interface Strategy {
  suggested_amount: string;
  entry_price_min: number;
  entry_price_max: number;
  exit_price: number;
  stop_loss: number;
  roi_potential: string;
  risk_level: string;
}

interface OptionAnalysis {
  option_name: string;
  current_price: number;
  price_percentage: number;
  volume_24h: number;
  volatility: number;
  stability: number;
  trend: string;
  confidence: number;
  recommendation: string;
  strategy: Strategy;
  token_id: string;
}

interface BestOption {
  option_name: string;
  score: number;
  recommendation: string;
  reason: string;
}

interface MarketAnalysis {
  market_question: string;
  total_options: number;
  options: OptionAnalysis[];
  best_option: BestOption;
}

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<MarketAnalysis | null>(null);

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
      setError(err instanceof Error ? err.message : 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };

  const getRecommendationClass = (recommendation: string) => {
    if (recommendation === 'ACHETER') return styles.buy;
    if (recommendation === 'ACHETER_PRUDENT') return styles.buy;
    if (recommendation === 'ATTENDRE') return styles.sell;
    return styles.hold;
  };

  const getTrendClass = (trend: string) => {
    if (trend === 'Haussière') return styles.good;
    if (trend === 'Baissière') return styles.bad;
    return styles.warning;
  };

  const getMetricClass = (value: number, metric: string) => {
    const numValue = typeof value === 'string' ? parseFloat(value as any) : value;
    
    if (metric === 'volatility') {
      if (numValue < 5) return styles.good;
      if (numValue < 8) return styles.warning;
      return styles.bad;
    }
    if (metric === 'stability') {
      if (numValue > 70) return styles.good;
      if (numValue > 50) return styles.warning;
      return styles.bad;
    }
    if (metric === 'confidence') {
      if (numValue > 70) return styles.good;
      if (numValue > 50) return styles.warning;
      return styles.bad;
    }
    return '';
  };

  return (
    <div className={styles.container}>
      <Head>
        <title>Polymarket Strategy Analyzer V6</title>
        <meta name="description" content="Analysez toutes les options d'un marché Polymarket" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className={styles.header}>
        <h1>🎯 Polymarket Strategy Analyzer</h1>
        <p>Analysez n'importe quel marché avec TimesFM et obtenez une stratégie de trading</p>
        <span className={styles.badge}>V6 - Multi-Options</span>
      </div>

      <div className={styles.content}>
        <div className={styles.inputGroup}>
          <label htmlFor="urlInput">URL du Marché Polymarket</label>
          <input
            id="urlInput"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://polymarket.com/event/will-crude-oil-cl-hit-by-end-of-march"
            onKeyPress={(e) => e.key === 'Enter' && analyzeMarket()}
          />
          <p className={styles.hint}>
            💡 Entrez juste l'URL du marché (sans #). Toutes les options seront analysées !
          </p>
        </div>

        <button
          className={styles.button}
          onClick={analyzeMarket}
          disabled={loading}
        >
          {loading ? '⏳ Analyse en cours...' : '🚀 Analyser Toutes les Options'}
        </button>

        {loading && (
          <div className={styles.loading}>
            <div className={styles.spinner}></div>
            <p>Analyse de toutes les options avec TimesFM...</p>
            <p className={styles.loadingHint}>Cela peut prendre 10-20 secondes</p>
          </div>
        )}

        {error && (
          <div className={styles.error}>
            <strong>Erreur:</strong> {error}
          </div>
        )}

        {result && (
          <div className={styles.result}>
            {/* En-tête du marché */}
            <div className={styles.marketHeader}>
              <h2>{result.market_question}</h2>
              <div className={styles.marketStats}>
                <span className={styles.stat}>
                  📊 {result.total_options} options analysées
                </span>
              </div>
            </div>

            {/* Meilleure option mise en évidence */}
            <div className={styles.bestOption}>
              <div className={styles.bestOptionHeader}>
                <span className={styles.trophy}>🏆</span>
                <h3>Meilleure Opportunité</h3>
              </div>
              <div className={styles.bestOptionContent}>
                <div className={styles.bestOptionName}>{result.best_option.option_name}</div>
                <div className={styles.bestOptionScore}>Score: {result.best_option.score}/100</div>
                <div className={styles.bestOptionReason}>{result.best_option.reason}</div>
                <div className={`${styles.bestOptionReco} ${getRecommendationClass(result.best_option.recommendation)}`}>
                  {result.best_option.recommendation}
                </div>
              </div>
            </div>

            {/* Tableau comparatif */}
            <div className={styles.comparisonTable}>
              <h3>📊 Tableau Comparatif de Toutes les Options</h3>
              
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Option</th>
                      <th>Prix Actuel</th>
                      <th>Volatilité</th>
                      <th>Stabilité</th>
                      <th>Tendance</th>
                      <th>Confiance</th>
                      <th>Recommandation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.options.map((option, index) => {
                      const isBest = option.option_name === result.best_option.option_name;
                      return (
                        <tr key={index} className={isBest ? styles.bestRow : ''}>
                          <td className={styles.optionName}>
                            {isBest && <span className={styles.star}>⭐</span>}
                            {option.option_name}
                          </td>
                          <td>
                            <div className={styles.priceCell}>
                              <span className={styles.priceValue}>${option.current_price.toFixed(3)}</span>
                              <span className={styles.pricePercent}>({option.price_percentage.toFixed(1)}%)</span>
                            </div>
                          </td>
                          <td>
                            <span className={`${styles.metric} ${getMetricClass(option.volatility, 'volatility')}`}>
                              {option.volatility}%
                            </span>
                          </td>
                          <td>
                            <span className={`${styles.metric} ${getMetricClass(option.stability, 'stability')}`}>
                              {option.stability}/100
                            </span>
                          </td>
                          <td>
                            <span className={`${styles.trend} ${getTrendClass(option.trend)}`}>
                              {option.trend}
                            </span>
                          </td>
                          <td>
                            <span className={`${styles.metric} ${getMetricClass(option.confidence, 'confidence')}`}>
                              {option.confidence}%
                            </span>
                          </td>
                          <td>
                            <span className={`${styles.recommendation} ${getRecommendationClass(option.recommendation)}`}>
                              {option.recommendation}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Stratégies détaillées */}
            <div className={styles.strategies}>
              <h3>💡 Stratégies Détaillées par Option</h3>
              
              {result.options.map((option, index) => {
                const isBest = option.option_name === result.best_option.option_name;
                return (
                  <div key={index} className={`${styles.strategyCard} ${isBest ? styles.bestStrategy : ''}`}>
                    <div className={styles.strategyHeader}>
                      <h4>
                        {isBest && <span className={styles.star}>⭐</span>}
                        {option.option_name}
                      </h4>
                      <span className={`${styles.strategyReco} ${getRecommendationClass(option.recommendation)}`}>
                        {option.recommendation}
                      </span>
                    </div>
                    
                    <div className={styles.strategyGrid}>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>💵 Montant Suggéré:</span>
                        <span className={styles.strategyValue}>{option.strategy.suggested_amount}</span>
                      </div>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>🎯 Prix d'Entrée:</span>
                        <span className={styles.strategyValue}>
                          ${option.strategy.entry_price_min}-${option.strategy.entry_price_max}
                        </span>
                      </div>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>🎯 Prix de Sortie:</span>
                        <span className={styles.strategyValue}>${option.strategy.exit_price}+</span>
                      </div>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>🛑 Stop-Loss:</span>
                        <span className={styles.strategyValue}>${option.strategy.stop_loss}</span>
                      </div>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>💰 ROI Potentiel:</span>
                        <span className={styles.strategyValue}>{option.strategy.roi_potential}</span>
                      </div>
                      <div className={styles.strategyItem}>
                        <span className={styles.strategyLabel}>⚠️ Niveau de Risque:</span>
                        <span className={styles.strategyValue}>{option.strategy.risk_level}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <footer className={styles.footer}>
        <p>
          Made with ❤️ by ONA | Powered by TimesFM & Polymarket API | V6 Multi-Options
        </p>
      </footer>
    </div>
  );
}
