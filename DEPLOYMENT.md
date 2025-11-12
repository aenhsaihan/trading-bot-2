# Deployment Guide

## Streamlit Cloud Deployment

This app is configured to deploy on Streamlit Cloud with support for centralized exchanges (Binance, Coinbase, Kraken).

### Current Configuration

- **ccxt**: Pinned to version 4.4.0 to avoid `coincurve` build dependency
- **web3**: Included for DEX functionality (works without coincurve)
- **All other dependencies**: Standard Python packages

### Why ccxt 4.4.0?

Newer versions of `ccxt` (4.5+) include `coincurve` as a dependency, which requires:
- `pkg-config` (system-level tool)
- C compiler and build tools
- These are not available on Streamlit Cloud's build environment

Version 4.4.0 works perfectly for centralized exchanges without these requirements.

## DEX Functionality

### Current Status

✅ **DEX is supported** using `web3` library, which is already included in `requirements.txt`

The DEX implementation (`src/exchanges/dex/uniswap.py`) uses `web3` directly and does **not** require `coincurve`.

### Future: Full ccxt DEX Support

If you want to use `ccxt` for DEX operations (which includes `coincurve` for faster ECDSA signing):

1. **Local Development**: Install `requirements-dex.txt`:
   ```bash
   pip install -r requirements-dex.txt
   ```

2. **Streamlit Cloud**: You'll need to either:
   - Wait for Streamlit Cloud to support `pkg-config` and build tools
   - Use a different deployment platform (e.g., Heroku, Railway, AWS)
   - Or use `web3` directly (current approach) which works fine

### Performance Note

`coincurve` provides faster ECDSA signing (~0.05ms vs ~45ms), but `ccxt` will automatically fall back to pure Python ECDSA if `coincurve` is not available. For most use cases, this performance difference is negligible.

## Updating Dependencies

When updating dependencies:

1. **Test locally first** in a virtual environment
2. **Check if new versions require build tools** (like `coincurve` does)
3. **Update `requirements.txt`** if safe for Streamlit Cloud
4. **Update `requirements-dex.txt`** for optional DEX dependencies

