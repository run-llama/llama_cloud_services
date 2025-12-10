# llama-cloud-services

## 0.5.1

### Patch Changes

- d5b18a0: Fix publishing

## 0.5.0

### Minor Changes

- 576c3d9: feat: support zod v4 & v3

  Adds support for zod v4 while maintaining backward compatibility with v3.
  - Updated zod peer dependency to accept both v3 and v4: `^3.25.76 || ^4.0.0`
  - Migrated all import statements to use `zod/v4` import path for compatibility

### Patch Changes

- c8321d2: Improve parse results polling
- 576c3d9: Support zod v3 an v4

## 0.4.3

### Patch Changes

- 71db318: Add tier and version

## 0.4.2

### Patch Changes

- bfaec79: Update for new page number params

## 0.4.1

### Patch Changes

- f3233de: Propagate retrieval metadata to retriever nodes

## 0.4.0

### Minor Changes

- f293547: Switch to keyword arguments rather than positional args

## 0.3.10

### Patch Changes

- fee516d: Adding LlamaClassify among the available LlamaCloud services

## 0.3.9

### Patch Changes

- 5d4cabd: Add ImageNode support in TypeScript

## 0.3.8

### Patch Changes

- 6e0f2f4: Agent data extraction citations can be undefined

## 0.3.7

### Patch Changes

- d028397: Update llama-cloud api version, and integrate with agent data deletion

## v0.1.0

First release for `llama-cloud-services`.
