import Image from 'next/image';
import type { HTMLAttributes } from 'react';
import dynamic from 'next/dynamic';
import { cn } from '../../lib/utils';

const UserIcon = dynamic(() => import('lucide-react/lib/esm/icons/user'));

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  size?: number;
}

export default function Avatar({
  src,
  alt = 'avatar',
  size = 32,
  className,
  ...props
}: AvatarProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-center overflow-hidden rounded-full bg-white/5',
        className,
      )}
      style={{ width: size, height: size }}
      {...props}
    >
      {src ? (
        <Image
          src={src}
          alt={alt}
          width={size}
          height={size}
          className="h-full w-full object-cover"
        />
      ) : (
        <UserIcon className="h-2/3 w-2/3 text-muted-foreground" />
      )}
    </div>
  );
}
