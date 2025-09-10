'use client';

import { useEffect, useState } from 'react';
import { z } from 'zod';
import { ZForm } from '../../components/forms/ZForm';
import { FormSection } from '../../components/forms/FormSection';
import { Field } from '../../components/forms/Field';
import { SubmitBar } from '../../components/forms/SubmitBar';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import Skeleton from '../../components/Skeleton';
import { useToast } from '../../components/ToastProvider';
import { useAuth } from '../../lib/auth';
import { apiFetch } from '../../lib/api';

const schema = z
  .object({
    listenBrainzUser: z.string().optional(),
    listenBrainzToken: z.string().optional(),
    useGpu: z.boolean().default(false),
    useStems: z.boolean().default(false),
    useExcerpts: z.boolean().default(false),
  })
  .refine(
    (d) =>
      (!d.listenBrainzUser && !d.listenBrainzToken) ||
      (d.listenBrainzUser && d.listenBrainzToken),
    {
      path: ['listenBrainzToken'],
      message: 'ListenBrainz user and token required together',
    },
  );

type SettingsValues = z.infer<typeof schema>;

export default function Settings() {
  const [defaults, setDefaults] = useState<SettingsValues>();
  const [lfmUser, setLfmUser] = useState('');
  const [lfmConnected, setLfmConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const { show } = useToast();
  const { userId } = useAuth();

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    apiFetch('/api/settings')
      .then((r) => r.json())
      .then(
        (data: Partial<
          SettingsValues & { lastfmUser: string; lastfmConnected: boolean }
        >) => {
          setDefaults({
            listenBrainzUser: data.listenBrainzUser || '',
            listenBrainzToken: data.listenBrainzToken || '',
            useGpu: !!data.useGpu,
            useStems: !!data.useStems,
            useExcerpts: !!data.useExcerpts,
          });
          setLfmUser(data.lastfmUser || '');
          setLfmConnected(!!data.lastfmConnected);
        },
      )
      .catch(() => {
        /* ignore */
      })
      .finally(() => setLoading(false));
  }, [userId]);

  async function handleSubmit(values: SettingsValues) {
    setMessage('');
    const res = await apiFetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const errs = Array.isArray(data.detail)
        ? data.detail
        : data.detail
        ? [data.detail]
        : ['Error saving settings'];
      show({ title: errs.join(', '), kind: 'error' });
      return;
    }
    setMessage('Settings saved');
    show({ title: 'Settings saved', kind: 'success' });
  }

  async function handleConnect() {
    const callback = encodeURIComponent(
      `${window.location.origin}/lastfm/callback`,
    );
    const res = await apiFetch(`/api/auth/lastfm/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) {
      window.location.href = data.url;
    } else {
      show({ title: 'Failed to connect to Last.fm', kind: 'error' });
    }
  }

  async function handleDisconnect() {
    const res = await apiFetch('/api/auth/lastfm/session', {
      method: 'DELETE',
    });
    if (!res.ok) {
      show({ title: 'Failed to disconnect Last.fm', kind: 'error' });
      return;
    }
    setLfmUser('');
    setLfmConnected(false);
    show({ title: 'Disconnected Last.fm', kind: 'success' });
  }

  return (
    <section className="space-y-6">
      <ZForm
        schema={schema}
        defaultValues={defaults}
        onSubmit={handleSubmit}
        className="space-y-6"
      >
        <FormSection title="ListenBrainz">
          {loading ? (
            <Skeleton className="h-24" />
          ) : (
            <>
              <Field name="listenBrainzUser" label="Username">
                {(field) => (
                  <Input
                    placeholder="ListenBrainz username"
                    {...field}
                  />
                )}
              </Field>
              <Field
                name="listenBrainzToken"
                label="Token"
                help="Find this token in your ListenBrainz settings"
              >
                {(field) => <Input placeholder="Token" {...field} />}
              </Field>
            </>
          )}
        </FormSection>

        <FormSection title="Last.fm">
          {loading ? (
            <Skeleton className="h-24" />
          ) : lfmConnected ? (
            <div className="flex items-center gap-2">
              <span>Connected as {lfmUser}</span>
              <Button type="button" onClick={handleDisconnect}>
                Disconnect
              </Button>
            </div>
          ) : (
            <Button type="button" onClick={handleConnect}>
              Connect Last.fm
            </Button>
          )}
        </FormSection>

        <FormSection title="Options">
          {loading ? (
            <Skeleton className="h-24" />
          ) : (
            <>
              <Field name="useGpu" label="Use GPU">
                {(field) => (
                  <Input
                    type="checkbox"
                    className="h-4 w-4"
                    {...field}
                    checked={field.value}
                  />
                )}
              </Field>
              <Field name="useStems" label="Extract stems">
                {(field) => (
                  <Input
                    type="checkbox"
                    className="h-4 w-4"
                    {...field}
                    checked={field.value}
                  />
                )}
              </Field>
              <Field name="useExcerpts" label="Use excerpts">
                {(field) => (
                  <Input
                    type="checkbox"
                    className="h-4 w-4"
                    {...field}
                    checked={field.value}
                  />
                )}
              </Field>
            </>
          )}
        </FormSection>

        <SubmitBar />
        {message && <div role="status">{message}</div>}
      </ZForm>
    </section>
  );
}
