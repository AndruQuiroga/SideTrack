'use client';

import { motion, useTransform, type MotionValue } from 'framer-motion';
import { Button } from '../ui/button';
import { useToast } from '../ToastProvider';
import { Dialog, DialogContent, DialogTrigger } from '../ui/dialog';

interface Props {
  onLike: () => void | Promise<void>;
  onSkip: () => void | Promise<void>;
  onHideArtist: () => void | Promise<void>;
  likeProgress: MotionValue<number>;
  skipProgress: MotionValue<number>;
  hideProgress: MotionValue<number>;
}

const MotionButton = motion(Button);

export default function RecActions({
  onLike,
  onSkip,
  onHideArtist,
  likeProgress,
  skipProgress,
  hideProgress,
}: Props) {
  const { show } = useToast();

  const likeScale = useTransform(likeProgress, [0, 1], [1, 1.06]);
  const likeY = useTransform(likeProgress, (value) => -6 * value);
  const likeShadow = useTransform(likeProgress, (value) =>
    `0 0 0 ${12 * value}px rgba(74, 222, 128, ${0.35 * value})`,
  );

  const skipScale = useTransform(skipProgress, [0, 1], [1, 1.06]);
  const skipY = useTransform(skipProgress, (value) => -6 * value);
  const skipShadow = useTransform(skipProgress, (value) =>
    `0 0 0 ${12 * value}px rgba(56, 189, 248, ${0.35 * value})`,
  );

  const hideScale = useTransform(hideProgress, [0, 1], [1, 1.06]);
  const hideY = useTransform(hideProgress, (value) => -6 * value);
  const hideShadow = useTransform(hideProgress, (value) =>
    `0 0 0 ${12 * value}px rgba(248, 113, 113, ${0.4 * value})`,
  );

  const ActionButtons = ({ focusFirst = false }: { focusFirst?: boolean }) => (
    <>
      <MotionButton
        autoFocus={focusFirst}
        style={{ scale: likeScale, y: likeY, boxShadow: likeShadow }}
        onClick={async () => {
          await onLike();
          show({ title: 'Saved', kind: 'success' });
        }}
      >
        Like
      </MotionButton>
      <MotionButton
        variant="outline"
        style={{ scale: skipScale, y: skipY, boxShadow: skipShadow }}
        onClick={async () => {
          await onSkip();
          show({ title: 'Skipped', kind: 'info' });
        }}
      >
        Skip
      </MotionButton>
      <MotionButton
        variant="ghost"
        style={{ scale: hideScale, y: hideY, boxShadow: hideShadow }}
        onClick={async () => {
          await onHideArtist();
          show({ title: 'Artist hidden', kind: 'success' });
        }}
      >
        Hide artist
      </MotionButton>
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
            <ActionButtons focusFirst />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

