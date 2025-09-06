# Test Factories

Factories for generating core models in tests.

## Usage

```python
from tests.factories import TrackFactory, FeatureFactory

tr = TrackFactory()
session.add(tr)
session.flush()
feat = FeatureFactory(track_id=tr.track_id)
session.add(feat)
session.commit()
```

### Available factories

- `TrackFactory`
- `FeatureFactory`
- `EmbeddingFactory`
- `UserFactory`

### Traits

- `FeatureFactory.zero` – zeroed-out feature values.
- `EmbeddingFactory.unit` – unit vector embedding.
- `UserFactory.admin` – admin role user.
