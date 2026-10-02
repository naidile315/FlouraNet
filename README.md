# Online Nursery (Django)

Concise notes for local development, testing, and the smoke test included in the project.

Prerequisites
- Python 3.11+ (or the interpreter used in this workspace)
- Git (optional)
- (Optional) `ngrok` for webhook testing

Quick setup
1. Create and activate a virtualenv:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell (Windows)
```

2. Install runtime requirements:

```powershell
pip install -r requirements.txt
```

Notes: a full environment capture was saved to `requirements.txt`.

Run the app
1. Apply migrations and (optionally) create a superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

2. (Optional) Seed sample data:

```powershell
python seed_data.py
```

3. Start the development server:

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

Smoke test (programmatic)
- A small programmatic smoke test is provided in `online_nursery/smoke_test.py`.
- It creates a test user (username `testuser` / password `testpass`), ensures a plant exists, logs in,
	adds the plant to cart and POSTs the checkout form. Run it with:

```powershell
python online_nursery\smoke_test.py
```

Payments / Webhooks
- Payment integration is optional. Set keys in `online_nursery/settings.py` when using Razorpay:

```python
# Example (test keys)
RAZORPAY_KEY_ID = ''
RAZORPAY_KEY_SECRET = ''
RAZORPAY_WEBHOOK_SECRET = 'your_webhook_secret'
```

- For local webhook testing, expose your server with `ngrok` and set the webhook URL to
	`https://<ngrok-id>.ngrok.io/payment/webhook/` in the Razorpay dashboard.

Files of interest
- `online_nursery/` — Django project
- `nursery_app/` — main app (models, views, templates)
- `media/` — uploaded plant images
- `static/` — CSS and JS (includes new `static/js/auth.js` for login recent-credentials UX)
- `online_nursery/smoke_test.py` — programmatic smoke test (Django test client)

Cleanup & notes
- A full `pip freeze` was saved to `requirements.txt`.
- Unused media files can be audited with `scripts/list_plant_images.py`.

If you want, I can:
- add a `requirements-dev.txt` with test/dev tools extracted from `requirements.txt`,
- or keep `requirements.txt` as a full freeze for exact reproducibility.

Questions or next steps: confirm if you want `requirements.txt` to contain the full freeze, or
to keep the trimmed runtime list and produce a `requirements-dev.txt`.

