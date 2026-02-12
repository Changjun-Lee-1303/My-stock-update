
import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, 
  Search, 
  Wallet, 
  Settings, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  Menu, 
  X, 
  ExternalLink, 
  Bell, 
  ShieldAlert, 
  DollarSign, 
  PieChart as PieChartIcon, 
  ArrowRight,
  Plus
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer 
} from 'recharts';
import { analyzeTickerWithGemini } from './services/geminiService';
import { 
  StockData, 
  AppSettings, 
  AIResponse, 
  PortfolioItem, 
  AnalysisItem, 
  AppNotification 
} from './types';

// --- Helper Components ---

const GradeBadge: React.FC<{ grade: string }> = ({ grade }) => {
  const styles = {
    S: 'bg-amber-100 text-amber-700 border-amber-200',
    A: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    F: 'bg-red-100 text-red-700 border-red-200',
  };
  const style = styles[grade as keyof typeof styles] || styles.F;
  
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-black border ${style} shadow-sm`}>
      {grade} GRADE
    </span>
  );
};

const MarketIndexCard: React.FC<{ name: string; value: number; change: number }> = ({ name, value, change }) => {
  const isUp = change >= 0;
  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col min-w-[140px]">
      <span className="text-gray-400 text-xs font-bold uppercase">{name}</span>
      <span className="text-lg font-bold text-gray-800 mt-1">{value.toLocaleString()}</span>
      <span className={`text-xs font-bold flex items-center gap-1 mt-1 ${isUp ? 'text-red-500' : 'text-blue-500'}`}>
        {isUp ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
        {change > 0 ? '+' : ''}{change}%
      </span>
    </div>
  );
};

// --- Stock Card Component with Checklist & Buttons ---
interface StockCardProps {
  item: AnalysisItem;
  onClick: (item: AnalysisItem) => void;
  onBuy: (item: AnalysisItem) => void;
  onSell: (item: AnalysisItem) => void;
  settings: AppSettings;
}

const StockCard: React.FC<StockCardProps> = ({ item, onClick, onBuy, onSell, settings }) => {
  const { used_data, grade } = item;
  
  // Safe access to data
  const peg = used_data?.peg ?? 0;
  const growth = used_data?.revenueGrowth ?? 0;
  const price = used_data?.price ?? 0;
  const ma200 = used_data?.ma200 ?? 0;
  const gap = used_data?.gapRatio ?? 0;
  const rsi = used_data?.rsi ?? 0;
  
  // Logic Checks for Visualization
  const isPegGood = peg < settings.pegThreshold || (growth >= 30 && peg < 3.0);
  const isGrowthGood = growth > 0;
  const isTrendGood = price > ma200;
  const isGapGood = gap > settings.gapThreshold;
  const isRsiGood = rsi < settings.rsiThreshold;

  const CheckItem = ({ label, passed, value }: { label: string, passed: boolean, value: string }) => (
    <div className="flex items-center justify-between text-xs py-1 border-b border-gray-50 last:border-0">
      <div className="flex items-center gap-2 text-gray-600">
        {passed ? <CheckCircle size={14} className="text-emerald-500"/> : <XCircle size={14} className="text-red-400"/>}
        <span>{label}</span>
      </div>
      <span className={`font-mono font-medium ${passed ? 'text-gray-800' : 'text-red-400'}`}>{value}</span>
    </div>
  );

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden group">
      {/* Header */}
      <div className="p-5 border-b border-gray-50 bg-gradient-to-br from-white to-gray-50">
        <div className="flex justify-between items-start mb-2">
           <div>
             <h3 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors cursor-pointer" onClick={() => onClick(item)}>
               {item.ticker}
             </h3>
             <p className="text-xs text-gray-400 font-medium">{item.name || "Stock Analysis"}</p>
           </div>
           <GradeBadge grade={grade} />
        </div>
        
        <div className="flex justify-between items-end mt-4">
           <div>
              <span className="text-xs text-gray-400 block mb-1">Current Price</span>
              <span className="text-2xl font-bold text-gray-800">${price.toFixed(2)}</span>
           </div>
           <div className="text-right">
              <span className="text-xs text-gray-400 block mb-1">Gap Ratio</span>
              <span className={`text-lg font-bold ${gap > 0 ? 'text-emerald-500' : 'text-blue-500'}`}>
                {gap > 0 ? '+' : ''}{gap.toFixed(1)}%
              </span>
           </div>
        </div>
      </div>

      {/* Checklist Body */}
      <div className="p-5 space-y-1">
         <CheckItem label="PEG Ratio" passed={isPegGood} value={peg.toFixed(2)} />
         <CheckItem label="Revenue Growth" passed={isGrowthGood} value={`${growth > 0 ? '+' : ''}${growth}%`} />
         <CheckItem label="Trend (MA200)" passed={isTrendGood} value={isTrendGood ? 'Uptrend' : 'Downtrend'} />
         <CheckItem label="Gap Filter" passed={isGapGood} value={`${gap.toFixed(1)}%`} />
         <CheckItem label="RSI Check" passed={isRsiGood} value={rsi.toFixed(0)} />
      </div>

      {/* Footer Buttons */}
      <div className="p-4 bg-gray-50 flex gap-3">
        <button 
          onClick={(e) => { e.stopPropagation(); onBuy(item); }}
          className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2 rounded-lg font-bold text-sm shadow-sm shadow-emerald-200 transition-colors flex items-center justify-center gap-2"
        >
          <TrendingUp size={16}/> Buy
        </button>
        <button 
          onClick={(e) => { e.stopPropagation(); onSell(item); }}
          className="flex-1 bg-white border border-red-200 text-red-500 hover:bg-red-50 py-2 rounded-lg font-bold text-sm transition-colors flex items-center justify-center gap-2"
        >
          <TrendingDown size={16}/> Sell
        </button>
      </div>
    </div>
  );
};

// --- Modals ---

const StockDetailModal = ({ stock, onClose }: { stock: AnalysisItem; onClose: () => void }) => {
  if (!stock) return null;
  const d = stock.used_data;
  
  // Helper to format chart symbol
  const getTradingViewSymbol = (ticker: string) => {
    // If numeric (Korean stock likely), prepend KRX: or KOSDAQ:
    // Simple heuristic: if pure numbers, assume KRX for now or check extension
    if (/^\d+$/.test(ticker)) return `KRX:${ticker}`;
    if (ticker.endsWith('.KS')) return `KRX:${ticker.replace('.KS', '')}`;
    if (ticker.endsWith('.KQ')) return `KOSDAQ:${ticker.replace('.KQ', '')}`;
    return ticker; // Default US
  };

  const symbol = getTradingViewSymbol(stock.ticker);
  const chartUrl = `https://www.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=${symbol}&interval=D&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&popupwidth=1000&popupheight=650&locale=en`;

  // DeMark Logic
  const demarkBuy = d?.demarkLow ?? 0;
  const demarkSell = d?.demarkHigh ?? 0;
  const currentPrice = d?.price ?? 0;
  const openPrice = d?.openPrice ?? 0;

  let demarkStatus = "NEUTRAL";
  let demarkColor = "text-gray-500";
  let demarkMsg = "Price is within normal range.";

  if (openPrice > demarkSell) {
    demarkStatus = "GAP UP (OVERHEATED)";
    demarkColor = "text-red-500";
    demarkMsg = "Gap Up Alert! Price started above DeMark resistance. High risk of pullback.";
  } else if (openPrice < demarkBuy) {
    demarkStatus = "GAP DOWN (BARGAIN)";
    demarkColor = "text-emerald-500";
    demarkMsg = "Bargain Alert! Gap Down below DeMark support. Potential S-Class entry point.";
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center sticky top-0 bg-white z-10">
          <div>
             <h2 className="text-2xl font-black text-gray-900 flex items-center gap-3">
               {stock.ticker} <GradeBadge grade={stock.grade}/>
             </h2>
             <p className="text-gray-500 text-sm mt-1">{stock.name || "Detailed Analysis Report"}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-8">
          {/* DeMark Strategy Section */}
          <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
             <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                <div className="bg-blue-500 text-white p-1 rounded-md"><TrendingUp size={16}/></div>
                DeMark Strategy Analysis
             </h3>
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-100">
                   <span className="text-xs font-bold text-slate-400 uppercase">Today's Open</span>
                   <div className="text-2xl font-bold text-slate-800">${openPrice.toFixed(2)}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-100">
                   <span className="text-xs font-bold text-emerald-500 uppercase">Buy Target (Low)</span>
                   <div className="text-2xl font-bold text-emerald-600">${demarkBuy.toFixed(2)}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-100">
                   <span className="text-xs font-bold text-red-500 uppercase">Sell Target (High)</span>
                   <div className="text-2xl font-bold text-red-600">${demarkSell.toFixed(2)}</div>
                </div>
             </div>
             <div className={`mt-4 p-3 rounded-lg border bg-white flex items-start gap-3`}>
                {demarkStatus.includes('GAP') ? <AlertTriangle className={demarkColor} /> : <CheckCircle className={demarkColor}/>}
                <div>
                   <div className={`font-bold ${demarkColor}`}>{demarkStatus}</div>
                   <p className="text-sm text-slate-600">{demarkMsg}</p>
                </div>
             </div>
          </div>

          {/* Yahoo Finance Button */}
          <a 
            href={`https://finance.yahoo.com/quote/${stock.ticker}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="block w-full text-center bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            <ExternalLink size={18}/> View on Yahoo Finance
          </a>

          {/* TradingView Chart */}
          <div className="h-[500px] w-full bg-gray-50 rounded-xl border border-gray-200 overflow-hidden relative">
             <iframe 
                src={chartUrl}
                className="w-full h-full"
                frameBorder="0"
                allowTransparency
                scrolling="no"
             />
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Main App ---

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'HOME' | 'SEARCH' | 'PORTFOLIO'>('HOME');
  const [recommendations, setRecommendations] = useState<AnalysisItem[]>([]);
  const [marketIndices, setMarketIndices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalEquity, setTotalEquity] = useState(100000000); // 1억 Default
  const [vix, setVix] = useState(18.5);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isQuotaExceeded, setIsQuotaExceeded] = useState(false);
  const [cooldownTime, setCooldownTime] = useState(0);

  // Settings & Portfolio
  const [settings, setSettings] = useState<AppSettings>({
    vixThreshold: 30,
    pegThreshold: 1.5,
    rsiThreshold: 70,
    stopLossPercent: 10,
    gapThreshold: 5,
  });

  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [selectedStock, setSelectedStock] = useState<AnalysisItem | null>(null);
  
  // Modals state
  const [showSettings, setShowSettings] = useState(false);
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [editingPortfolioItem, setEditingPortfolioItem] = useState<PortfolioItem | null>(null);

  // Notifications
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);

  // --- Handlers ---

  const handleRefresh = async () => {
    if (loading || cooldownTime > 0) return;
    setLoading(true);
    setIsQuotaExceeded(false);

    // Call Gemini with RECOMMEND context (Top 20 Analysis)
    const response = await analyzeTickerWithGemini(totalEquity, vix, [], settings, 'RECOMMEND');

    if (response.market_status === "Quota Exceeded") {
       setIsQuotaExceeded(true);
       setCooldownTime(60); // 60s Cooldown
    } else {
       setRecommendations(response.analysis_result || []);
       setMarketIndices(response.market_indices || []);
       setLastUpdated(new Date());
       
       // Check for Buy Opportunities (S Grade)
       const sGrades = response.analysis_result.filter(r => r.grade === 'S');
       if (sGrades.length > 0) {
          addNotification('BUY_ALERT', 'S-Class Opportunity', `Found ${sGrades.length} S-Grade stocks! Check Home.`);
       }
    }
    setLoading(false);
  };

  const addNotification = (type: 'SELL_ALERT' | 'BUY_ALERT', title: string, message: string) => {
    const newNotif: AppNotification = {
      id: Date.now().toString(),
      type, title, message, timestamp: new Date()
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  const handleCardBuy = (item: AnalysisItem) => {
    // Open Portfolio Modal pre-filled
    const existing = portfolio.find(p => p.ticker === item.ticker);
    if (existing) {
       setEditingPortfolioItem(existing);
    } else {
       setEditingPortfolioItem({
          id: '',
          ticker: item.ticker,
          quantity: 0,
          avgPrice: item.used_data?.price || 0,
          currentPrice: item.used_data?.price,
          ma200: item.used_data?.ma200
       });
    }
    setShowPortfolioModal(true);
  };

  const handleCardSell = (item: AnalysisItem) => {
     const existing = portfolio.find(p => p.ticker === item.ticker);
     if (existing) {
        setEditingPortfolioItem(existing);
        setShowPortfolioModal(true);
     } else {
        alert("You don't own this stock to sell.");
     }
  };

  const savePortfolioItem = (item: PortfolioItem) => {
     if (item.id) {
        // Edit
        setPortfolio(prev => prev.map(p => p.id === item.id ? item : p));
     } else {
        // Add
        setPortfolio(prev => [...prev, { ...item, id: Date.now().toString() }]);
     }
     setShowPortfolioModal(false);
     setEditingPortfolioItem(null);
  };

  const removePortfolioItem = (id: string) => {
     setPortfolio(prev => prev.filter(p => p.id !== id));
     setShowPortfolioModal(false);
     setEditingPortfolioItem(null);
  };

  // Cooldown Timer
  useEffect(() => {
    if (cooldownTime > 0) {
       const timer = setInterval(() => setCooldownTime(t => t - 1), 1000);
       return () => clearInterval(timer);
    }
  }, [cooldownTime]);

  // --- Render Sections ---

  const renderSidebar = () => (
    <div className="hidden lg:flex flex-col w-64 bg-white border-r border-gray-100 h-screen fixed left-0 top-0 z-20">
      <div className="p-6 border-b border-gray-50">
        <h1 className="text-xl font-black text-blue-600 flex items-center gap-2">
           <ShieldAlert /> Smart Asset AI
        </h1>
        <p className="text-xs text-gray-400 mt-2">Yahoo Finance Powered</p>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
         <div className="text-xs font-bold text-gray-400 uppercase mb-2 px-2">Menu</div>
         <button onClick={() => setActiveTab('HOME')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors ${activeTab === 'HOME' ? 'bg-blue-50 text-blue-600' : 'text-gray-500 hover:bg-gray-50'}`}>
            <LayoutDashboard size={20}/> Dashboard
         </button>
         <button onClick={() => setActiveTab('PORTFOLIO')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors ${activeTab === 'PORTFOLIO' ? 'bg-blue-50 text-blue-600' : 'text-gray-500 hover:bg-gray-50'}`}>
            <Wallet size={20}/> My Portfolio
         </button>
         <button onClick={() => setShowSettings(true)} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors text-gray-500 hover:bg-gray-50`}>
            <Settings size={20}/> Strategy Settings
         </button>
      </nav>

      <div className="p-4 bg-gray-50 m-4 rounded-xl">
         <h4 className="font-bold text-gray-800 text-sm mb-2">Key Logic</h4>
         <ul className="text-xs text-gray-500 space-y-1">
            <li>• VIX Shield (Limit: {settings.vixThreshold})</li>
            <li>• PEG Filter (Max: {settings.pegThreshold})</li>
            <li>• Gap Hunter (Min: {settings.gapThreshold}%)</li>
            <li>• AI Grade (S/A/F)</li>
         </ul>
      </div>
    </div>
  );

  const renderHome = () => {
    const filteredRecommendations = recommendations.filter(r => r.grade === 'S' || r.grade === 'A');
    
    return (
      <div className="space-y-8 max-w-7xl mx-auto">
        {/* Header Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
           <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
              <div className="flex justify-between items-start">
                 <div>
                    <span className="text-sm font-bold text-gray-400 block mb-1">Total Equity</span>
                    <span className="text-3xl font-black text-gray-900">₩{totalEquity.toLocaleString()}</span>
                 </div>
                 <div className="bg-blue-100 p-2 rounded-lg text-blue-600"><DollarSign size={24}/></div>
              </div>
           </div>
           
           <div className={`p-6 rounded-2xl border shadow-sm ${vix >= 30 ? 'bg-red-50 border-red-100' : 'bg-emerald-50 border-emerald-100'}`}>
              <div className="flex justify-between items-start">
                 <div>
                    <span className={`text-sm font-bold block mb-1 ${vix >= 30 ? 'text-red-400' : 'text-emerald-400'}`}>Market Status</span>
                    <span className={`text-3xl font-black ${vix >= 30 ? 'text-red-600' : 'text-emerald-600'}`}>
                       {vix >= 30 ? 'HALTED' : 'ACTIVE'}
                    </span>
                    <span className="text-sm font-medium opacity-70 block mt-1">VIX: {vix}</span>
                 </div>
                 <div className={`p-2 rounded-lg ${vix >= 30 ? 'bg-red-200 text-red-700' : 'bg-emerald-200 text-emerald-700'}`}>
                    {vix >= 30 ? <ShieldAlert size={24}/> : <TrendingUp size={24}/>}
                 </div>
              </div>
           </div>

           <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col justify-center">
               <button 
                  onClick={handleRefresh} 
                  disabled={loading || cooldownTime > 0}
                  className={`w-full py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all ${
                     loading ? 'bg-gray-100 text-gray-400' : 
                     cooldownTime > 0 ? 'bg-orange-100 text-orange-500' :
                     'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-200'
                  }`}
               >
                  {loading ? <RefreshCw className="animate-spin" /> : <RefreshCw />}
                  {loading ? 'Analyzing...' : cooldownTime > 0 ? `Wait ${cooldownTime}s` : 'Daily Analysis'}
               </button>
               {lastUpdated && <span className="text-xs text-center text-gray-400 mt-2">Last: {lastUpdated.toLocaleTimeString()}</span>}
           </div>
        </div>

        {/* Market Indices (Horizontal Scroll) */}
        {marketIndices.length > 0 && (
           <div className="overflow-x-auto pb-4 scrollbar-hide">
              <div className="flex gap-4 min-w-max">
                 {marketIndices.map(idx => (
                    <MarketIndexCard key={idx.name} name={idx.name} value={idx.value} change={idx.changePercent} />
                 ))}
              </div>
           </div>
        )}

        {/* Alert Banner for Quota */}
        {isQuotaExceeded && (
          <div className="bg-orange-50 border border-orange-200 text-orange-700 p-4 rounded-xl flex items-center gap-3">
             <AlertTriangle />
             <div>
                <span className="font-bold">API Limit Reached.</span>
                <span className="text-sm block">Please wait {cooldownTime} seconds before refreshing again.</span>
             </div>
          </div>
        )}

        {/* Recommendations Grid */}
        <div>
           <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
              <CheckCircle className="text-blue-600"/> S & A Grade Recommendations
           </h2>
           
           {loading && recommendations.length === 0 ? (
               <div className="bg-white border border-gray-100 rounded-2xl p-12 text-center">
                  <RefreshCw className="animate-spin text-blue-500 mx-auto mb-4" size={32}/>
                  <p className="text-gray-500">Scanning Top 100 Market Data across NASDAQ/KOSPI/KOSDAQ...</p>
               </div>
           ) : filteredRecommendations.length > 0 ? (
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredRecommendations.map((item, idx) => (
                     <StockCard 
                        key={`${item.ticker}-${idx}`} 
                        item={item} 
                        onClick={setSelectedStock} 
                        onBuy={handleCardBuy}
                        onSell={handleCardSell}
                        settings={settings}
                     />
                  ))}
               </div>
           ) : (
               <div className="bg-white border border-gray-100 rounded-2xl p-12 text-center text-gray-400">
                  {recommendations.length > 0 
                     ? "No S or A Grade stocks found today. Market might be weak." 
                     : "Press 'Daily Analysis' to start scanning the market."}
               </div>
           )}
        </div>
      </div>
    );
  };

  const renderPortfolio = () => {
    // Calculate totals
    const totalInvested = portfolio.reduce((acc, p) => acc + (p.avgPrice * p.quantity), 0);
    const currentValuation = portfolio.reduce((acc, p) => acc + ((p.currentPrice || p.avgPrice) * p.quantity), 0);
    const totalPL = currentValuation - totalInvested;
    const totalPLPercent = totalInvested > 0 ? (totalPL / totalInvested) * 100 : 0;
    const cash = totalEquity - totalInvested; // Simple logic: Cash = Equity - Invested Cost (assuming Equity is total capital)

    // Chart Data (Mocking a trend line from Cost to Current)
    const chartData = [
       { name: 'Invested', value: totalInvested },
       { name: 'Current', value: currentValuation }
    ];

    return (
      <div className="space-y-8 max-w-7xl mx-auto">
         {/* Portfolio Summary */}
         <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
               <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
                  <span className="text-sm font-bold text-gray-400">Net Worth (Est)</span>
                  <div className="text-3xl font-black text-gray-900 mt-1">
                     ₩{(cash + currentValuation).toLocaleString()}
                  </div>
               </div>
               <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
                  <span className="text-sm font-bold text-gray-400">Total Profit/Loss</span>
                  <div className={`text-3xl font-black mt-1 ${totalPL >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                     {totalPL >= 0 ? '+' : ''}₩{totalPL.toLocaleString()} 
                     <span className="text-lg ml-2">({totalPLPercent.toFixed(2)}%)</span>
                  </div>
               </div>
               <div className="col-span-1 sm:col-span-2 bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
                   <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2"><PieChartIcon size={18}/> Allocation</h4>
                   <div className="h-4 flex rounded-full overflow-hidden bg-gray-100">
                      <div className="bg-blue-500 h-full" style={{ width: `${Math.min(100, (totalInvested/totalEquity)*100)}%` }} />
                   </div>
                   <div className="flex justify-between text-xs font-bold mt-2">
                      <span className="text-blue-500">Stocks: {((totalInvested/totalEquity)*100).toFixed(1)}%</span>
                      <span className="text-gray-400">Cash: {(100 - ((totalInvested/totalEquity)*100)).toFixed(1)}%</span>
                   </div>
               </div>
            </div>

            {/* Performance Chart */}
            <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col justify-between">
               <h4 className="font-bold text-gray-800 mb-2">Performance Trend</h4>
               <div className="h-[150px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                     <AreaChart data={chartData}>
                        <defs>
                           <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor={totalPL >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0.8}/>
                              <stop offset="95%" stopColor={totalPL >= 0 ? "#10b981" : "#ef4444"} stopOpacity={0}/>
                           </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                        <XAxis dataKey="name" hide/>
                        <YAxis hide domain={['auto', 'auto']}/>
                        <RechartsTooltip />
                        <Area type="monotone" dataKey="value" stroke={totalPL >= 0 ? "#10b981" : "#ef4444"} fillOpacity={1} fill="url(#colorVal)" />
                     </AreaChart>
                  </ResponsiveContainer>
               </div>
               <p className="text-xs text-gray-400 text-center">Cost Basis vs Current Value</p>
            </div>
         </div>

         {/* Holdings List */}
         <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-gray-50 flex justify-between items-center">
               <h3 className="font-bold text-lg text-gray-900">Holdings ({portfolio.length})</h3>
               <button onClick={() => { setEditingPortfolioItem({ id: '', ticker: '', quantity: 0, avgPrice: 0 }); setShowPortfolioModal(true); }} className="text-blue-600 font-bold text-sm flex items-center gap-1 hover:bg-blue-50 px-3 py-1 rounded-lg">
                  <Plus size={16}/> Add Stock
               </button>
            </div>
            
            <div className="divide-y divide-gray-50">
               {portfolio.map(item => {
                  const currPrice = item.currentPrice || item.avgPrice;
                  const val = currPrice * item.quantity;
                  const cost = item.avgPrice * item.quantity;
                  const pl = val - cost;
                  const plPer = (pl / cost) * 100;
                  
                  return (
                     <div key={item.id} className="p-5 flex flex-col md:flex-row justify-between items-center gap-4 hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => { setEditingPortfolioItem(item); setShowPortfolioModal(true); }}>
                        <div className="flex items-center gap-4 w-full md:w-auto">
                           <div className="bg-blue-100 text-blue-700 w-12 h-12 rounded-xl flex items-center justify-center font-black text-lg">
                              {item.ticker.substring(0, 1)}
                           </div>
                           <div>
                              <div className="font-bold text-gray-900 text-lg">{item.ticker}</div>
                              <div className="text-xs text-gray-400">{item.quantity} Shares @ ${item.avgPrice.toLocaleString()}</div>
                           </div>
                        </div>

                        <div className="flex items-center gap-8 w-full md:w-auto justify-between">
                           <div className="text-right">
                              <div className="text-xs text-gray-400 uppercase">Valuation</div>
                              <div className="font-bold text-gray-900">₩{val.toLocaleString()}</div>
                           </div>
                           <div className="text-right min-w-[100px]">
                              <div className="text-xs text-gray-400 uppercase">P/L</div>
                              <div className={`font-bold ${pl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                 {pl >= 0 ? '+' : ''}{pl.toLocaleString()}
                              </div>
                              <div className={`text-xs font-bold ${pl >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                 {plPer.toFixed(2)}%
                              </div>
                           </div>
                        </div>
                     </div>
                  );
               })}
               {portfolio.length === 0 && (
                  <div className="p-12 text-center text-gray-400">
                     Your portfolio is empty. Add a stock to track performance.
                  </div>
               )}
            </div>
         </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Mobile Header */}
      <div className="lg:hidden bg-white border-b border-gray-100 p-4 flex justify-between items-center sticky top-0 z-30">
         <span className="font-black text-blue-600 flex items-center gap-2"><ShieldAlert/> Smart AI</span>
         <button className="p-2 text-gray-500"><Menu/></button>
      </div>

      {renderSidebar()}

      <main className="lg:ml-64 p-4 lg:p-8 pt-20 lg:pt-8">
        {activeTab === 'HOME' && renderHome()}
        {activeTab === 'PORTFOLIO' && renderPortfolio()}
      </main>

      {/* Detail Modal */}
      {selectedStock && (
        <StockDetailModal stock={selectedStock} onClose={() => setSelectedStock(null)} />
      )}

      {/* Portfolio Add/Edit Modal */}
      {showPortfolioModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
           <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <h3 className="text-xl font-bold mb-4">{editingPortfolioItem?.id ? 'Edit Position' : 'Add Position'}</h3>
              <div className="space-y-4">
                 <div>
                    <label className="block text-xs font-bold text-gray-400 mb-1">Ticker Symbol</label>
                    <input 
                       className="w-full border border-gray-200 rounded-xl p-3 font-bold focus:outline-none focus:border-blue-500"
                       value={editingPortfolioItem?.ticker || ''}
                       onChange={e => setEditingPortfolioItem(prev => ({ ...prev!, ticker: e.target.value.toUpperCase() }))}
                       placeholder="e.g. NVDA"
                    />
                 </div>
                 <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-bold text-gray-400 mb-1">Quantity</label>
                        <input 
                           type="number"
                           className="w-full border border-gray-200 rounded-xl p-3 font-bold"
                           value={editingPortfolioItem?.quantity || 0}
                           onChange={e => setEditingPortfolioItem(prev => ({ ...prev!, quantity: Number(e.target.value) }))}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-bold text-gray-400 mb-1">Avg Buy Price</label>
                        <input 
                           type="number"
                           className="w-full border border-gray-200 rounded-xl p-3 font-bold"
                           value={editingPortfolioItem?.avgPrice || 0}
                           onChange={e => setEditingPortfolioItem(prev => ({ ...prev!, avgPrice: Number(e.target.value) }))}
                        />
                    </div>
                 </div>
              </div>
              <div className="flex gap-3 mt-6">
                 {editingPortfolioItem?.id && (
                    <button 
                       onClick={() => removePortfolioItem(editingPortfolioItem.id)}
                       className="px-4 py-3 rounded-xl font-bold text-red-500 bg-red-50 hover:bg-red-100"
                    >
                       Remove
                    </button>
                 )}
                 <div className="flex-1 flex gap-3">
                    <button onClick={() => setShowPortfolioModal(false)} className="flex-1 py-3 font-bold text-gray-400 hover:text-gray-600">Cancel</button>
                    <button onClick={() => editingPortfolioItem && savePortfolioItem(editingPortfolioItem)} className="flex-1 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700">Save</button>
                 </div>
              </div>
           </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettings && (
         <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
               <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold">Strategy Settings</h3>
                  <button onClick={() => setShowSettings(false)}><X className="text-gray-400"/></button>
               </div>
               
               <div className="space-y-5">
                  {[
                     { label: 'VIX Safety Limit', key: 'vixThreshold', desc: 'Halt trading if VIX is above this.' },
                     { label: 'Max PEG Ratio', key: 'pegThreshold', desc: 'Acceptable valuation limit.' },
                     { label: 'Max RSI (Overbought)', key: 'rsiThreshold', desc: 'Avoid buying if RSI > limit.' },
                     { label: 'Min Gap Ratio %', key: 'gapThreshold', desc: 'Buy only if undervalued by % vs sector.' }
                  ].map((field) => (
                     <div key={field.key}>
                        <div className="flex justify-between mb-1">
                           <label className="font-bold text-gray-700">{field.label}</label>
                           <span className="font-mono font-bold text-blue-600">{settings[field.key as keyof AppSettings]}</span>
                        </div>
                        <input 
                           type="range" 
                           min="0" max="100" step="0.1"
                           className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                           value={settings[field.key as keyof AppSettings]}
                           onChange={(e) => setSettings(prev => ({ ...prev, [field.key]: Number(e.target.value) }))}
                        />
                        <p className="text-xs text-gray-400 mt-1">{field.desc}</p>
                     </div>
                  ))}
               </div>
               
               <button onClick={() => setShowSettings(false)} className="w-full bg-blue-600 text-white font-bold py-3 rounded-xl mt-6">
                  Apply Settings
               </button>
            </div>
         </div>
      )}
    </div>
  );
};

export default App;
