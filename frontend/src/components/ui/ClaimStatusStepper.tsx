import React from 'react';
import { ClaimStatus } from './StatusPill';
import { Check } from 'lucide-react';

interface ClaimStatusStepperProps {
  currentStatus: ClaimStatus;
  statuses: { id: string; label: string }[];
}

export function ClaimStatusStepper({ currentStatus, statuses }: ClaimStatusStepperProps) {
  const currentIndex = statuses.findIndex((s) => s.id === currentStatus);

  return (
    <div className="w-full">
      <div className="hidden md:flex items-center justify-between">
        {statuses.map((status, index) => {
          const isCompleted = index < currentIndex;
          const isActive = index === currentIndex;
          
          return (
            <div key={status.id} className="flex flex-col items-center relative flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 transition-colors ${
                isActive ? 'bg-brand-500 text-white' : 
                isCompleted ? 'bg-green-500 text-white' : 'bg-charcoal-200 dark:bg-charcoal-700 text-charcoal-500'
              }`}>
                {isCompleted ? <Check className="w-4 h-4" /> : <span className="text-sm">{index + 1}</span>}
              </div>
              <p className={`mt-2 text-sm font-medium ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-charcoal-500'}`}>
                {status.label}
              </p>
              {index < statuses.length - 1 && (
                <div className={`absolute top-4 left-1/2 w-full h-0.5 -z-10 ${
                  isCompleted ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`} />
              )}
            </div>
          );
        })}
      </div>
      
      <div className="flex md:hidden flex-col gap-4 relative">
        {statuses.map((status, index) => {
          const isCompleted = index < currentIndex;
          const isActive = index === currentIndex;
          
          return (
            <div key={status.id} className="flex items-center gap-4 relative">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 shrink-0 ${
                isActive ? 'bg-brand-500 text-white' : 
                isCompleted ? 'bg-green-500 text-white' : 'bg-charcoal-200 dark:bg-charcoal-700 text-charcoal-500'
              }`}>
                {isCompleted ? <Check className="w-4 h-4" /> : <span className="text-sm">{index + 1}</span>}
              </div>
              <p className={`text-sm font-medium ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-charcoal-500'}`}>
                {status.label}
              </p>
              {index < statuses.length - 1 && (
                <div className={`absolute top-8 left-4 w-0.5 h-full -ml-px -z-10 ${
                  isCompleted ? 'bg-green-500' : 'bg-charcoal-200 dark:bg-charcoal-700'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
