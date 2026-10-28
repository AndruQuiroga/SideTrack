import { FeatureUnavailable } from '../../components/feature-unavailable';
export default function ProfilePage() {
  return (
    <FeatureUnavailable
      title="Profiles"
      description="Profile analytics are unavailable. Open Listening from the navigation to see your stored listening history."
    />
  );
}
