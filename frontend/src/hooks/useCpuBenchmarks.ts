import { useState, useCallback } from 'react';
import type { CpuBenchmark } from '../types/config';

/**
 * Hook to fetch CPU benchmarks for multiple CPUs
 *
 * First tries to fetch from cache, then fetches from web if needed
 */
export function useCpuBenchmarks() {
  const [cpuBenchmarks, setCpuBenchmarks] = useState<Record<string, CpuBenchmark | null>>({});
  const [loading, setLoading] = useState(false);

  const fetchBenchmarks = useCallback(async (cpuNames: string[], shouldFetch = false) => {
    if (cpuNames.length === 0) return;

    setLoading(true);

    try {
      const response = await fetch('/server-list/api/cpu/benchmark/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cpus: cpuNames, fetch: shouldFetch }),
      });

      if (response.ok) {
        const data = await response.json();
        const benchmarks: Record<string, CpuBenchmark | null> = {};
        let hasMissingData = false;

        for (const cpu of cpuNames) {
          const result = data.results?.[cpu];
          benchmarks[cpu] = result?.success ? result.data : null;
          if (!result?.success) {
            hasMissingData = true;
          }
        }

        setCpuBenchmarks(benchmarks);

        // If some data is missing and we haven't tried fetching yet, retry with fetch=true
        if (hasMissingData && !shouldFetch) {
          fetchBenchmarks(cpuNames, true);
        }
      }
    } catch {
      console.log('CPU benchmark API not available');
    } finally {
      setLoading(false);
    }
  }, []);

  return { cpuBenchmarks, fetchBenchmarks, loading };
}
