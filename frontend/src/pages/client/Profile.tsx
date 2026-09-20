import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Skeleton, ErrorBanner } from '@/components/ui';

import type { Profile as ProfileData } from '@/lib/types';

function Profile() {
  const queryClient = useQueryClient();
  const [phone, setPhone] = useState('');
  const [licenceExpiry, setLicenceExpiry] = useState('');

  const { data: profile, isLoading, error } = useQuery<ProfileData>({
    queryKey: ['me'],
    queryFn: () => api.get<ProfileData>('/me'),
  });

  useEffect(() => {
    if (profile) {
      setPhone(profile.phone || '');
      setLicenceExpiry(profile.client?.drivers_licence_expiry || '');
    }
  }, [profile]);

  const updateProfile = useMutation({
    mutationFn: (data: { phone?: string; drivers_licence_expiry?: string }) => api.patch('/me', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] });
      alert('Profile updated successfully');
    },
    onError: (err: any) => {
      alert(`Error updating profile: ${err.message}`);
    }
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorBanner error={error as Error} />;
  if (!profile) return null;

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold text-charcoal">My Profile</h1>

      <div className="bg-white p-6 rounded-lg shadow border border-gray-100 space-y-6">
        <h2 className="text-xl font-bold text-charcoal border-b pb-2">Personal Information</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Full Name</label>
            <div className="p-2 bg-gray-50 rounded border border-gray-200 text-charcoal">{profile.full_name}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Email</label>
            <div className="p-2 bg-gray-50 rounded border border-gray-200 text-charcoal">{profile.email}</div>
          </div>
        </div>

        <div>
          <label htmlFor="profile-phone" className="block text-sm font-medium text-charcoal mb-1">Phone Number</label>
          <div className="flex gap-4">
            <input 
              id="profile-phone" type="tel" 
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="flex-1 p-2 border rounded focus:ring-brand-500 focus:border-brand-500 text-charcoal" 
            />
            <button 
              onClick={() => updateProfile.mutate({ phone })}
              disabled={phone === profile.phone || updateProfile.isPending}
              className="px-4 py-2 bg-brand-500 text-white rounded font-medium disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="profile-licence" className="block text-sm font-medium text-charcoal mb-1">Drivers Licence Expiry</label>
          <div className="flex gap-4">
            <input 
              id="profile-licence" type="date" 
              value={licenceExpiry}
              onChange={(e) => setLicenceExpiry(e.target.value)}
              className="flex-1 p-2 border rounded focus:ring-brand-500 focus:border-brand-500 text-charcoal" 
            />
            <button 
              onClick={() => updateProfile.mutate({ drivers_licence_expiry: licenceExpiry })}
              disabled={licenceExpiry === profile.client?.drivers_licence_expiry || updateProfile.isPending}
              className="px-4 py-2 bg-brand-500 text-white rounded font-medium disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      </div>

      {profile.client?.adviser && (
        <div className="bg-charcoal text-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold text-brand-500 mb-4 border-b border-gray-700 pb-2">Your Adviser</h2>
          <p className="font-bold text-lg mb-2">{profile.client?.adviser.full_name}</p>
          <div className="space-y-2 text-sm">
            <p>Email: <a href={`mailto:${profile.client?.adviser.email}`} className="text-brand-500 hover:underline">{profile.client?.adviser.email}</a></p>
            {profile.client?.adviser.phone && <p>Phone: <a href={`tel:${profile.client?.adviser.phone}`} className="text-brand-500 hover:underline">{profile.client?.adviser.phone}</a></p>}
          </div>
        </div>
      )}
    </div>
  );
}

export default Profile;
