import os

# Settings requires this to construct even when a test never touches a real
# Firestore/Pub-Sub client (they're all mocked in unit tests).
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "corporate-test")
