import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner } from '@/components/ui';

interface Insurer {
  id: string;
  name: string;
}

function RegisterClaim() {
  const [step, setStep] = useState(0);
  const [claimId, setClaimId] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data: insurers, isLoading } = useQuery<Insurer[]>({
    queryKey: ['insurers'],
    queryFn: () => api.get<Insurer[]>('/insurers'),
  });

  const createDraft = useMutation({
    mutationFn: (insurer_id: string) => api.post('/claims', { insurer_id }),
    onSuccess: (data: any) => {
      setClaimId(data.id);
      setStep(1);
    }
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;

  const handleNext = () => setStep(s => Math.min(s + 1, 7));
  const handlePrev = () => setStep(s => Math.max(s - 1, 0));

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-charcoal mb-4">Register a Claim</h1>
        <div className="w-full bg-gray-200 h-2 rounded-full">
          <div className="bg-brand-500 h-2 rounded-full transition-all" style={{ width: `${(step / 7) * 100}%` }}></div>
        </div>
        <p className="text-right text-xs text-gray-500 mt-2">Step {step} of 7</p>
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-charcoal">Select Insurer</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {insurers?.map((ins) => (
              <button 
                key={ins.id}
                onClick={() => createDraft.mutate(ins.id)}
                className="p-4 border rounded-lg hover:border-brand-500 hover:bg-gray-50 text-left"
              >
                <span className="font-bold">{ins.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step > 0 && step < 7 && (
        <div className="bg-white p-6 rounded-lg shadow space-y-6">
          <h2 className="text-xl font-bold text-charcoal">
            {step === 1 && 'Incident Details'}
            {step === 2 && 'Police Report'}
            {step === 3 && 'Driver Information'}
            {step === 4 && 'Witnesses'}
            {step === 5 && 'Third Parties'}
            {step === 6 && 'Uploads'}
          </h2>
          
          <div className="min-h-[200px] flex items-center justify-center text-gray-500 bg-gray-50 rounded border border-dashed">
            [ Form fields for Step {step} goes here. Auto-saves on Next. ]
          </div>

          <div className="flex justify-between pt-4 border-t">
            <button onClick={handlePrev} className="px-4 py-2 border rounded text-charcoal hover:bg-gray-100">Back</button>
            <button onClick={handleNext} className="px-4 py-2 bg-brand-500 text-white rounded hover:bg-gray-800">Next Step</button>
          </div>
        </div>
      )}

      {step === 7 && (
        <div className="bg-white p-6 rounded-lg shadow space-y-6">
          <h2 className="text-xl font-bold text-charcoal">Review and Submit</h2>
          <div className="p-4 bg-gray-50 rounded border">
            <p className="text-sm text-gray-600 mb-2">Summary of entered data...</p>
          </div>
          
          <div className="flex justify-between pt-4 border-t">
            <button onClick={handlePrev} className="px-4 py-2 border rounded text-charcoal hover:bg-gray-100">Back</button>
            <button 
              onClick={() => navigate(`/claims/${claimId}`)} 
              className="px-6 py-2 bg-brand-500 text-white font-bold rounded hover:bg-yellow-500 shadow"
            >
              Submit Claim
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default RegisterClaim;
