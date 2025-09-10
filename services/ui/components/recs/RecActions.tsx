'use client';

import { Button } from '../ui/button';
import { useToast } from '../ToastProvider';
import { Dialog, DialogContent, DialogTrigger } from '../ui/dialog';

interface Props {
  onLike: () => void | Promise<void>;
  onSkip: () => void | Promise<void>;
  onHideArtist: () => void | Promise<void>;
}

export default function RecActions({ onLike, onSkip, onHideArtist }: Props) {
  const { show } = useToast();

  const ActionButtons = () => (
    <>
      <Button
        onClick={async () => {
          await onLike();
          show({ title: 'Saved', kind: 'success' });
        }}
      >
        Like
      </Button>
      <Button
        variant="outline"
        onClick={async () => {
          await onSkip();
          show({ title: 'Skipped', kind: 'info' });
        }}
      >
        Skip
      </Button>
      <Button
        variant="ghost"
        onClick={async () => {
          await onHideArtist();
          show({ title: 'Artist hidden', kind: 'success' });
        }}
      >
        Hide artist
      </Button>
    </>
  );

  return (
    <>
      <div className="hidden gap-2 md:flex">
        <ActionButtons />
      </div>
      <Dialog>
        <DialogTrigger asChild>
          <Button className="w-full md:hidden">Actions</Button>
        </DialogTrigger>
        <DialogContent className="md:hidden bottom-0 left-0 right-0 top-auto translate-x-0 translate-y-0 max-w-full rounded-t-lg p-4">
          <div className="grid gap-2">
            <ActionButtons />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

