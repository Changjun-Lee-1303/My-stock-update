import React from 'react';
import { AIResponse, AnalysisItem } from '../types';
import { ShieldAlert, CheckCircle, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface AnalysisResultsProps {
  data: AIResponse | null;
}

const GradeBadge = ({ grade }: { grade: string }) => {
  const colors = {
    S: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    A: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50',
    F: 'bg-red-500/20 text-red-400 border-red-500/50',
  };
  const colorClass = colors[grade as keyof typeof colors] || colors.F;

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${colorClass}`}>
      GRADE {grade}
    </span>
  );
};

const ActionBadge = ({ action }: { action: string }) => {
  if (action === 'BUY') return <span className="text-emerald-400 font-bold flex items-center gap-1"><TrendingUp size={14}/> BUY</span>;
  if (action === 'SELL') return <span className="text-red-400 font-bold flex items-center gap-1"><TrendingDown size={14}/> SELL</span>;
  return <span className="text-slate-400 font-bold flex items-center gap-1"><Minus size={14}/> PASS</span>;
};

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ data }) => {
  // Defensive: Ensure data and market_status exist. Use fallback if data is null.
  const status = data?.market_status || "Pending";
  const isHalted = status.includes('Halted');
  const results = data?.analysis_result || [];

  // Prepare chart data
  const allocatedData = results
    .filter(item => item.allocation_percent > 0)
    .map(item => ({
      name: item.ticker,
      value: item.allocation_percent,
    }));
  
  const totalAllocated = allocatedData.reduce((acc, curr) => acc + curr.value, 0);
  const cashData = { name: 'CASH (Reserve)', value: Math.max(0, 1 - totalAllocated) };
  
  const chartData = [...allocatedData, cashData];
  const COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#64748b'];

  if (!data) {
    return <div className="text-slate-500 italic text-center p-4">Waiting for analysis...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Market Status Banner */}
      <div className={`p-4 rounded-xl border flex items-center gap-3 ${isHalted ? 'bg-red-900/20 border-red-500/50 text-red-200' : 'bg-emerald-900/20 border-emerald-500/50 text-emerald-200'}`}>
        {isHalted ? <ShieldAlert size={24} /> : <CheckCircle size={24} />}
        <div>
          <h3 className="font-bold text-lg">Market Status: {status}</h3>
          <p className="text-sm opacity-80">{isHalted ? 'Trading is halted due to high volatility (VIX >= 30). Protect capital.' : 'Market conditions allow for active filtering and allocation.'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List of Analyzed Stocks */}
        <div className="lg:col-span-2 space-y-4">
          {results.length === 0 ? (
            <div className="p-8 text-center text-slate-500 bg-slate-800 rounded-xl border border-slate-700">
               No analysis results available.
            </div>
          ) : (
            results.map((item, idx) => (
              <div key={idx} className="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h4 className="text-xl font-bold text-white">{item.ticker}</h4>
                    <GradeBadge grade={item.grade} />
                    <ActionBadge action={item.action} />
                  </div>
                  <div className="flex gap-2 text-sm text-slate-400 flex-wrap">
                    {item.reasons.map((reason, rIdx) => (
                      <span key={rIdx} className="bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col items-end min-w-[140px] text-right bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Allocation</span>
                  <span className={`text-xl font-mono font-bold ${item.allocation_percent > 0 ? 'text-white' : 'text-slate-600'}`}>
                    {(item.allocation_percent * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-emerald-400">{item.recommended_amount}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Allocation Chart */}
        <div className="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col items-center justify-center min-h-[300px]">
          <h4 className="text-white font-semibold mb-4 w-full text-left flex items-center gap-2">
            <AlertTriangle size={16} className="text-yellow-500"/> Suggested Portfolio
          </h4>
          <div className="w-full h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.name.includes('CASH') ? '#334155' : COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }}
                  itemStyle={{ color: '#f8fafc' }}
                  formatter={(value: number) => `${(value * 100).toFixed(0)}%`}
                />
                <Legend iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-500 text-center mt-2">
            Allocation logic strictly follows the S-Grade (30%) and A-Grade (10%) rules.
          </p>
        </div>
      </div>
    </div>
  );
};