import Skeleton from './Skeleton';
import { cn } from '../lib/utils';

export default function ChartSkeleton({ className }: { className?: string }) {
  return <Skeleton className={cn('aspect-[4/3] h-[clamp(240px,40vh,380px)]', className)} />;
}
