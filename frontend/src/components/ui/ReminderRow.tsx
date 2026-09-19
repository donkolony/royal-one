import React, { useState } from 'react';
import { Button } from './Button';
import { format, parseISO, isPast, isToday, addDays } from 'date-fns';
import { Check } from 'lucide-react';

interface Reminder {
  id: string;
  title: string;
  due_date: string;
  status: 'pending' | 'completed';
}

export function ReminderRow({ reminder, onComplete }: { reminder: Reminder; onComplete: (id: string) => Promise<void> }) {
  const [loading, setLoading] = useState(false);

  const handleComplete = async () => {
    setLoading(true);
    try {
      await onComplete(reminder.id);
    } finally {
      setLoading(false);
    }
  };

  const due = parseISO(reminder.due_date);
  const isOverdue = isPast(due) && !isToday(due);
  const isDueSoon = !isOverdue && due <= addDays(new Date(), 3);

  const urgencyColor = isOverdue ? 'text-red-600' : isDueSoon ? 'text-amber-600' : 'text-charcoal-600';

  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-charcoal-800 border border-charcoal-100 dark:border-charcoal-700 rounded-lg shadow-sm">
      <div>
        <h4 className="font-medium text-charcoal-900 dark:text-white">{reminder.title}</h4>
        <p className={`text-sm ${urgencyColor} flex items-center gap-2 mt-1`}>
          {format(due, 'dd MMM yyyy')}
          {isOverdue && <span className="text-xs bg-red-100 text-red-800 px-1.5 py-0.5 rounded">Overdue</span>}
        </p>
      </div>
      {reminder.status !== 'completed' && (
        <Button variant="ghost" size="sm" onClick={handleComplete} loading={loading} aria-label="Mark done">
          <Check className="w-5 h-5 text-green-600" />
        </Button>
      )}
    </div>
  );
}
