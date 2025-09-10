import { redirect } from 'next/navigation';

export default function Page() {
  redirect('/explore?tab=moods');
}
