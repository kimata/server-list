import { useEffect, useRef, useState, useCallback } from 'react';

interface UseEventSourceOptions {
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
  reconnectInterval?: number;
}

interface UseEventSourceReturn {
  isConnected: boolean;
  reconnect: () => void;
  close: () => void;
}

export function useEventSource(
  url: string,
  options: UseEventSourceOptions = {}
): UseEventSourceReturn {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Store callbacks in refs to avoid dependency issues
  const onMessageRef = useRef(options.onMessage);
  const onErrorRef = useRef(options.onError);
  const reconnectInterval = options.reconnectInterval ?? 5000;

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = options.onMessage;
    onErrorRef.current = options.onError;
  }, [options.onMessage, options.onError]);

  const close = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (eventSourceRef.current && eventSourceRef.current.readyState === EventSource.OPEN) {
      return;
    }

    close();

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      // Ignore dummy keepalive messages
      if (event.data === 'dummy') return;

      if (onMessageRef.current) {
        onMessageRef.current(event);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);

      if (eventSource.readyState === EventSource.CLOSED) {
        // Only reconnect if this is still our active connection
        if (eventSourceRef.current === eventSource) {
          reconnectTimeoutRef.current = window.setTimeout(connect, reconnectInterval);
        }
      }

      if (onErrorRef.current) {
        onErrorRef.current(new Event('error'));
      }
    };
  }, [url, reconnectInterval, close]);

  useEffect(() => {
    connect();

    return () => {
      close();
    };
  }, [connect, close]);

  return {
    isConnected,
    reconnect: connect,
    close,
  };
}
