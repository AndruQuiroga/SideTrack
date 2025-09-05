AXES = ["energy", "valence", "danceability", "brightness", "pumpiness"]

# default scoring methods
DEFAULT_METHOD = "zero"  # zero-shot using embeddings
# Note: adding "heur" (heuristic feature-based) keeps backward compatibility
SUPPORTED_METHODS = {"zero", "logreg", "heur"}
