/** Browser-safe gallery read types and in-memory interaction state. No API credentials. */
import type { SinglesSessionRead, SinglesSessionDetail } from '@sidetrack/api-client';
import type { Access } from './server-api';

export type GalleryGroup = { summary: SinglesSessionRead; detail: Access<SinglesSessionDetail> };
export type GalleryBatch = { groups: GalleryGroup[]; nextOffset: number | null };
export type GalleryActions = {
  older: (offset: number) => Promise<Access<GalleryBatch>>;
  retry: (id: string) => Promise<Access<SinglesSessionDetail>>;
};
export type GalleryState = {
  access: Access<GalleryBatch>;
  pending: string[];
  olderFailed: boolean;
};

/** One mounted gallery only. Stable group keys preserve native disclosure state. */
export class GalleryStore {
  private state: GalleryState;
  private listeners = new Set<() => void>();
  private active = new Set<string>();
  private epoch = 0;
  constructor(initial: Access<GalleryBatch>) {
    this.state = { access: initial, pending: [], olderFailed: false };
  }
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private publish(next: GalleryState) {
    this.state = next;
    this.listeners.forEach((listener) => listener());
  }
  private deny(access: Access<never>) {
    this.epoch++;
    this.publish({ access, pending: [], olderFailed: false });
  }
  async older(action: GalleryActions['older']) {
    if (this.active.has('older') || this.state.access.state !== 'ok') return;
    const offset = this.state.access.data.nextOffset;
    if (offset === null) return;
    this.active.add('older');
    const epoch = this.epoch;
    this.publish({ ...this.state, pending: [...this.active], olderFailed: false });
    try {
      const result = await action(offset);
      if (epoch !== this.epoch || this.state.access.state !== 'ok') return;
      if (result.state === 'signed-out' || result.state === 'forbidden') return this.deny(result);
      if (result.state !== 'ok') {
        this.publish({ ...this.state, olderFailed: true });
        return;
      }
      const groups = [...this.state.access.data.groups];
      const known = new Set(groups.map((group) => group.summary.id));
      for (const group of result.data.groups) {
        if (!known.has(group.summary.id)) {
          groups.push(group);
          known.add(group.summary.id);
        }
      }
      this.publish({
        ...this.state,
        access: { state: 'ok', data: { groups, nextOffset: result.data.nextOffset } },
      });
    } catch {
      if (epoch === this.epoch && this.state.access.state === 'ok')
        this.publish({ ...this.state, olderFailed: true });
    } finally {
      this.active.delete('older');
      if (epoch === this.epoch) this.publish({ ...this.state, pending: [...this.active] });
    }
  }
  async retry(id: string, action: GalleryActions['retry']) {
    if (this.active.has(id) || this.state.access.state !== 'ok') return;
    if (!this.state.access.data.groups.some((group) => group.summary.id === id)) return;
    this.active.add(id);
    const epoch = this.epoch;
    this.publish({ ...this.state, pending: [...this.active] });
    try {
      let result: Access<SinglesSessionDetail>;
      try {
        result = await action(id);
      } catch {
        result = { state: 'unavailable' };
      }
      if (epoch !== this.epoch || this.state.access.state !== 'ok') return;
      if (result.state === 'signed-out' || result.state === 'forbidden') return this.deny(result);
      if (result.state === 'ok' && result.data.id !== id) result = { state: 'unavailable' };
      const groups = this.state.access.data.groups.map((group) =>
        group.summary.id === id ? { ...group, detail: result } : group,
      );
      this.publish({
        ...this.state,
        access: { state: 'ok', data: { ...this.state.access.data, groups } },
      });
    } finally {
      this.active.delete(id);
      if (epoch === this.epoch) this.publish({ ...this.state, pending: [...this.active] });
    }
  }
}
