import React from 'react';
import { act } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent, { PointerEventsCheckLevel } from '@testing-library/user-event';
import RecCard, { type Rec } from './RecCard';
import ToastProvider from '../ToastProvider';

jest.mock('framer-motion', () => {
  const motion = (Component: React.ComponentType<any>) =>
    React.forwardRef<HTMLDivElement, any>((props, ref) => <Component ref={ref} {...props} />);

  motion.div = React.forwardRef<HTMLDivElement, any>((props, ref) => {
    const {
      children,
      onDragEnd,
      style,
      dragConstraints,
      dragElastic,
      dragMomentum,
      dragSnapToOrigin,
      ...rest
    } = props;
    const startRef = React.useRef<number | null>(null);

    const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
      startRef.current = event.clientX;
      rest.onPointerDown?.(event);
    };

    const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
      rest.onPointerUp?.(event);
      if (startRef.current !== null) {
        const offset = event.clientX - startRef.current;
        onDragEnd?.(event, {
          offset: { x: offset, y: 0 },
          delta: { x: offset, y: 0 },
          point: { x: event.clientX, y: event.clientY },
          velocity: { x: 0, y: 0 },
        });
        startRef.current = null;
      }
    };

    const resolvedStyle = style && 'x' in style ? { ...style, transform: undefined } : style;

    return (
      <div
        ref={ref}
        {...rest}
        style={resolvedStyle}
        data-drag-constraints={dragConstraints ? 'mock' : undefined}
        data-drag-elastic={dragElastic ? 'mock' : undefined}
        data-drag-momentum={dragMomentum ? 'mock' : undefined}
        data-drag-snap={dragSnapToOrigin ? 'mock' : undefined}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
      >
        {children}
      </div>
    );
  });

  return {
    __esModule: true,
    motion,
    useMotionValue: (initial: number) => {
      let value = initial;
      return {
        set: (v: number) => {
          value = v;
        },
        get: () => value,
      };
    },
    useTransform: () => 0,
  };
});

jest.mock('../../lib/artwork', () => ({
  getArtworkUrl: jest.fn(() => Promise.resolve(null)),
}));

const baseRec: Rec = {
  title: 'Test Track',
  artist: 'Test Artist',
};

const renderCard = async () => {
  const onLike = jest.fn();
  const onSkip = jest.fn();
  const onHideArtist = jest.fn();

  await act(async () => {
    render(
      <ToastProvider>
        <RecCard rec={baseRec} onLike={onLike} onSkip={onSkip} onHideArtist={onHideArtist} />
      </ToastProvider>,
    );
  });

  return {
    card: screen.getByTestId('rec-card'),
    onLike,
    onSkip,
    onHideArtist,
  };
};

const dragCard = async (
  card: HTMLElement,
  deltaX: number,
  user = userEvent.setup({ pointerEventsCheck: PointerEventsCheckLevel.Never }),
) => {
  const startX = 150;
  await user.pointer([
    { target: card, coords: { clientX: startX, clientY: 0 }, keys: '[MouseLeft>]' },
    { target: card, coords: { clientX: startX + deltaX, clientY: 0 } },
    { target: card, coords: { clientX: startX + deltaX, clientY: 0 }, keys: '[/MouseLeft]' },
  ]);
};

describe('RecCard drag gestures', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('calls onLike when dragged to the right beyond the threshold', async () => {
    const { card, onLike, onSkip, onHideArtist } = await renderCard();
    const user = userEvent.setup({ pointerEventsCheck: PointerEventsCheckLevel.Never });

    await dragCard(card, 180, user);

    await waitFor(() => expect(onLike).toHaveBeenCalledTimes(1));
    expect(onSkip).not.toHaveBeenCalled();
    expect(onHideArtist).not.toHaveBeenCalled();
  });

  it('calls onSkip when dragged to the left beyond the skip threshold', async () => {
    const { card, onLike, onSkip, onHideArtist } = await renderCard();
    const user = userEvent.setup({ pointerEventsCheck: PointerEventsCheckLevel.Never });

    await dragCard(card, -140, user);

    await waitFor(() => expect(onSkip).toHaveBeenCalledTimes(1));
    expect(onLike).not.toHaveBeenCalled();
    expect(onHideArtist).not.toHaveBeenCalled();
  });

  it('calls onHideArtist when dragged far to the left', async () => {
    const { card, onLike, onSkip, onHideArtist } = await renderCard();
    const user = userEvent.setup({ pointerEventsCheck: PointerEventsCheckLevel.Never });

    await dragCard(card, -260, user);

    await waitFor(() => expect(onHideArtist).toHaveBeenCalledTimes(1));
    expect(onLike).not.toHaveBeenCalled();
    expect(onSkip).not.toHaveBeenCalled();
  });

  it('does nothing when released before reaching a threshold', async () => {
    const { card, onLike, onSkip, onHideArtist } = await renderCard();
    const user = userEvent.setup({ pointerEventsCheck: PointerEventsCheckLevel.Never });

    await dragCard(card, 30, user);

    await waitFor(() => {
      expect(onLike).not.toHaveBeenCalled();
      expect(onSkip).not.toHaveBeenCalled();
      expect(onHideArtist).not.toHaveBeenCalled();
    });
  });
});
