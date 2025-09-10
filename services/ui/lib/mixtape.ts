export type MixtapeTrack = { track_id: number; title?: string };

let queue: MixtapeTrack[] = [];

export function addToMixtape(track: MixtapeTrack) {
  queue.push(track);
}

export function getMixtape() {
  return queue;
}

export function clearMixtape() {
  queue = [];
}

export function handleMixtapeDrop(e: React.DragEvent) {
  const data = e.dataTransfer.getData('application/json');
  if (data) {
    try {
      const track = JSON.parse(data) as MixtapeTrack;
      addToMixtape(track);
    } catch {
      /* noop */
    }
  }
}

