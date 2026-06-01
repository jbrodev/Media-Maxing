"""AI provider implementations.

Mock is the default. Real provider adapters are scaffolds that raise
``ProviderDisabledError`` unless explicit environment configuration
turns them on. Batch 3 keeps real provider calls disabled by policy.
"""
