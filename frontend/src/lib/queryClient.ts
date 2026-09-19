import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api' // Note: defined in api.ts

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // Don't retry 4xx errors
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
    },
  },
})
