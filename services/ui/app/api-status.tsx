'use client';
import { useEffect, useState } from 'react';

export default function ApiStatus() {
  const [status, setStatus] = useState<string>('loading...');
  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/health` : '/api/health')
      .then(r => r.json())
      .then(j => setStatus(`${j.status} (db: ${j.db})`))
      .catch(() => setStatus('error'));
  }, []);
  return <span>API: {status}</span>;
}

