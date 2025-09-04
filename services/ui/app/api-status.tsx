'use client';
import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

export default function ApiStatus() {
  const [status, setStatus] = useState<string>('loading...');
  useEffect(() => {
    apiFetch('/health')
      .then(r => r.json())
      .then(j => setStatus(`${j.status} (db: ${j.db})`))
      .catch(() => setStatus('error'));
  }, []);
  return <span>API: {status}</span>;
}

