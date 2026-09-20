import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './errors'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // A 4xx is the server saying no (validation, forbidden, not found, rate limit): retrying cannot help.
        // Network failures (status 0) and 5xx are worth a couple more tries.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 2
      },
    },
    mutations: { retry: false },
  },
})
