import React from 'react';
import { Card } from './Card';
import { format, parseISO } from 'date-fns';

interface NetWorth {
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  as_of: string;
}

export function NetWorthCard({ netWorth }: { netWorth: NetWorth }) {
  const formatZAR = (cents: number) => {
    const rands = cents / 100;
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR' }).format(rands);
  };

  const isNegative = netWorth.net_worth < 0;

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-sm font-medium text-charcoal-500 dark:text-charcoal-400">Total Net Worth</h3>
        <p className={`text-3xl font-bold mt-1 ${isNegative ? 'text-red-600 dark:text-red-400' : 'text-charcoal-900 dark:text-white'}`}>
          {formatZAR(netWorth.net_worth)}
        </p>
        <p className="text-xs text-charcoal-400 mt-1">
          As of {format(parseISO(netWorth.as_of), 'dd MMM yyyy')}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 border-t border-charcoal-100 dark:border-charcoal-700 pt-4">
        <div>
          <p className="text-xs text-charcoal-500">Total Assets</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_assets)}</p>
        </div>
        <div>
          <p className="text-xs text-charcoal-500">Total Liabilities</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_liabilities)}</p>
        </div>
      </div>
    </Card>
  );
}
