
export interface StockData {
  id: string;
  ticker: string;
  price: number;
  ma200: number;
  rsi: number;
  peg: number;
  revenueGrowth: number;
  gapRatio: number;
  name?: string; 
}

export interface AppSettings {
  vixThreshold: number; // Default 30
  pegThreshold: number; // Default 1.5
  rsiThreshold: number; // Default 70
  stopLossPercent: number; // Default 10 (-10%)
  gapThreshold: number; // Default 5 (%)
}

export interface PortfolioItem {
  id: string; // Unique ID for editing
  ticker: string;
  avgPrice: number;
  quantity: number;
  currentPrice?: number; // Fetched/Estimated
  ma200?: number; // Fetched/Estimated
}

export type Grade = 'S' | 'A' | 'F';
export type Action = 'BUY' | 'PASS' | 'SELL';

export interface AnalysisItem {
  ticker: string;
  name?: string;
  grade: Grade;
  action: Action;
  allocation_percent: number;
  recommended_amount: string;
  reasons: string[];
  used_data: {
    price: number;
    openPrice: number; // Today's Open
    prevClose: number; // Yesterday's Close
    ma200: number;
    rsi: number;
    peg: number;
    revenueGrowth: number;
    gapRatio: number;
    demarkLow: number;  // Projected Low (Buy Limit)
    demarkHigh: number; // Projected High (Sell Limit)
  };
}

export interface MarketIndex {
  name: string;
  value: number;
  changePercent: number;
  status: 'UP' | 'DOWN' | 'FLAT';
}

export interface AIResponse {
  market_status: string;
  vix_used: number;
  market_indices?: MarketIndex[];
  analysis_result: AnalysisItem[];
}

// Added missing AppNotification interface
export interface AppNotification {
  id: string;
  type: 'SELL_ALERT' | 'BUY_ALERT';
  title: string;
  message: string;
  timestamp: Date;
}

export type Tab = 'HOME' | 'SEARCH' | 'PORTFOLIO';
