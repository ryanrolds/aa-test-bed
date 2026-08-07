"""Test support shared across the suite."""

# The project settings point the default cache at Redis because Alliance Auth
# insists on one at startup. That Redis outlives the test run, so any test that
# asserts on caching has to be pinned to a per-process cache instead — with a
# cache.clear() in setUp, since Django does not reset locmem between tests.
NO_REDIS_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
