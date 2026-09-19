import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string || 'https://placeholder.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string || 'placeholder'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export const getSession = async () => {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw error
  return data.session
}

const CLIENT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzYjg0MTI4NS03ZTNjLTVlMDUtOTQwMC1lNjZlZDM3Yzc2NDAiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3ODk4MzQzMTIsImV4cCI6MTc4OTg2MzExMn0.RrWEps62qrYcS3mUk2L-TaA3ATxtIlOEWJJRXj1FAlI";
const ADVISOR_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMTVhMzRkNi00ZDlmLTUzNTMtOTdmNC0xMmM0MWVhODM3N2QiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3ODk4MzQzMTMsImV4cCI6MTc4OTg2MzExM30.EJfn9KlkrOnTnQBbtt6dJ4lKVV2t5PJs0TF7yDulnQU";

export const getAccessToken = async () => {
  // DEV BYPASS: if a dev_role is set, return the hardcoded offline backend token
  const devRole = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem("dev_role") : null;
  if (devRole === 'client') return CLIENT_TOKEN;
  if (devRole === 'advisor') return ADVISOR_TOKEN;

  const session = await getSession()
  return session?.access_token || null
}

export const signOut = async () => {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem("dev_role");
  }
  await supabase.auth.signOut();
  window.location.href = '/sign-in';
}
