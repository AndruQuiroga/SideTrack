'use client';
import { useState } from 'react';
export function AlbumArt({ url, title }: { url?: string | null; title: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const usable = url && /^https?:\/\//i.test(url) && failedUrl !== url;
  return (
    <div className="album-art">
      {usable ? (
        <img
          src={url}
          alt={`Cover of ${title}`}
          width={400}
          height={400}
          onError={() => setFailedUrl(url)}
          loading="lazy"
        />
      ) : (
        <span className="art-unavailable">Artwork unavailable</span>
      )}
    </div>
  );
}
