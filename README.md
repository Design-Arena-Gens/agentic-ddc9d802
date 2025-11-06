# Forex Scanner

Simple command-line tool for retrieving live Forex exchange rates using the free [Alpha Vantage](https://www.alphavantage.co/) API.

## Requirements

- Python 3.9+
- `pip` for installing dependencies
- Alpha Vantage API key (free tier available)

## Setup

1. (Optional) Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Provide your Alpha Vantage API key via environment variable or CLI flag:

   ```bash
   export ALPHAVANTAGE_API_KEY=your_key_here
   ```

## Usage

Run the scanner with default pairs:

```bash
python forex_scanner.py
```

Specify custom pairs and refresh every 60 seconds:

```bash
python forex_scanner.py --pairs EUR/USD USD/JPY AUD/USD --refresh 60
```

Override the API key on the command line:

```bash
python forex_scanner.py --api-key your_key_here
```

The script prints the latest exchange rate, bid/ask (when available), and the last refreshed timestamp for each pair. API rate limits apply (5 calls/minute for free tier).

## Notes

- Handle Alpha Vantage throttling by increasing the refresh interval or limiting pairs.
- A non-zero exit code is returned if no quotes could be retrieved.
