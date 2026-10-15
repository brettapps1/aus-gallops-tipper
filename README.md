# 🐎 FormFav Racing Intelligence & Subscription Automation

Professional Australian gallops racing analytics, algorithmic barrier/weight trifecta selections, and 100% automated daily subscription dispatch.

## Features
- **Automated Daily Pipeline:** Fetches AU race cards, meetings, and runner metrics via FormFav API.
- **Trifecta Prediction Engine:** Algorithmic ranking based on barrier advantages and weight distributions.
- **Subscriber Packaging:** Automatically compiles daily Markdown & PDF intelligence booklets and packages them for subscriber delivery.
- **Robust Execution Wrapper:** Health-monitored automation runner (`run_subscription_automation.py`) with error logging.

## Usage
```bash
# Set your API key
export FORMFAV_API_KEY="your_api_key"

# Run automated daily subscription fetch & prediction pipeline
python3 scripts/racing/run_subscription_automation.py

# Dispatch subscriber intelligence package
python3 scripts/racing/dispatch_subscriber_intelligence.py
```
