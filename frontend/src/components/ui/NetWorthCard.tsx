import React from 'react';
import { Card } from './Card';
import { formatDate, formatZAR } from '../../lib/utils';
import type { NetWorth } from '../../lib/types';

/** Shows the API's NetWorth object as-is (GET /net-worth or dashboard.net_worth): amounts are integer cents. */
export function NetWorthCard({ netWorth }: { netWorth: NetWorth }) {
  const isNegative = netWorth.net_worth_cents < 0;

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-sm font-medium text-charcoal-500 dark:text-charcoal-400">Total net worth</h3>
        <p className={`text-3xl font-bold mt-1 ${isNegative ? 'text-red-600 dark:text-red-400' : 'text-charcoal-900 dark:text-white'}`}>
          {formatZAR(netWorth.net_worth_cents)}
        </p>
        <p className="text-xs text-charcoal-400 mt-1">As of {formatDate(netWorth.as_of)}</p>
      </div>
      <div className="grid grid-cols-2 gap-4 border-t border-charcoal-100 dark:border-charcoal-700 pt-4">
        <div>
          <p className="text-xs text-charcoal-500 dark:text-charcoal-400">Total assets</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_assets_cents)}</p>
        </div>
        <div>
          <p className="text-xs text-charcoal-500 dark:text-charcoal-400">Total liabilities</p>
          <p className="text-sm font-medium text-charcoal-900 dark:text-white">{formatZAR(netWorth.total_liabilities_cents)}</p>
        </div>
      </div>
    </Card>
  );
}
