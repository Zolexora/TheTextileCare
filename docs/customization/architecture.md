# Customisation Architecture

Customisation distinguishes between configuration and feature toggles.

## Configuration

- COD = disabled

## Feature flag

- loyalty = enabled

## Workflow configuration

```text
PICKED_UP -> PROCESSING -> QUALITY_CHECK -> READY
```

Custom capabilities are added to the shared platform rather than creating seller-specific forks.
