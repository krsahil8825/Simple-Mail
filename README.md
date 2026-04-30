# Simple Mail

A clean, production-minded FastAPI service for handling contact-form submissions and sending them through SMTP with an HTML email template.

Built for a simple workflow:

- validate incoming form data with Pydantic
- protect the endpoint with origin checks and rate limiting
- render a polished HTML email with Jinja2
- deliver mail through your SMTP provider

## Features

- FastAPI endpoint for form submissions
- SMTP-based email delivery with `EmailMessage`
- HTML email rendering via Jinja2
- Input validation with Pydantic v2
- Origin / referer allowlist protection
- Rate limiting with SlowAPI
- Environment-based configuration with `python-dotenv`
- Hidden API docs in non-debug mode

## Requirements

- Python 3.14 or newer
- `uv` package manager
- SMTP account credentials
- A verified recipient email address

## Installation

Clone the repository, then install dependencies with `uv`:

```bash
uv sync
```

If you want to run the app in an isolated environment managed by `uv`, this command is enough to create and sync the environment from `pyproject.toml`.

## Configuration

Create a `.env` file in the project root with the following variables:

```env
DEBUG=true
ALLOWED_HOSTS=localhost:3000,localhost:8000,127.0.0.1:3000,127.0.0.1:8000
RECIPIENT_EMAIL=recipient@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-username@example.com
SMTP_PASSWORD=your-smtp-password
```

### Environment Variables

- `DEBUG`: Enables FastAPI docs at `/docs` and `/redoc` when set to `true`
- `ALLOWED_HOSTS`: Comma-separated list of allowed request origins or referers
- `RECIPIENT_EMAIL`: Destination email that receives the form submissions
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port, usually `587`
- `SMTP_USER`: SMTP login username
- `SMTP_PASSWORD`: SMTP login password

## Running the App

Start the development server with `uv`:

```bash
uv run uvicorn main:app --reload
```

The API will usually be available at:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs` when `DEBUG=true`

## API

### `POST /submit-form`

Submits a contact form and sends an email to the configured recipient.

#### Request Body

```json
{
    "name": "Kumar Sahil",
    "email": "krsahil8825@gmail.com",
    "message": "Hello, this is a test message."
}
```

#### Example cURL

```bash
curl -X POST http://127.0.0.1:8000/submit-form \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "name": "Kumar Sahil",
    "email": "krsahil8825@gmail.com",
    "message": "Hello, this is a test message."
  }'
```

#### Success Response

```json
{
    "message": "Email sent successfully",
    "status": "success"
}
```

#### Common Error Responses

- `403 Forbidden`: The request origin is not allowed
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: SMTP delivery failed

## How It Works

1. The endpoint receives a JSON payload containing `name`, `email`, and `message`.
2. Pydantic validates and trims the input.
3. The server checks the `Origin` or `Referer` header against `ALLOWED_HOSTS`.
4. The message is rendered into the HTML template in `templates/email_template.html`.
5. The email is sent through the configured SMTP server.

## Security Notes

- Requests are blocked unless their origin or referer matches the configured allowlist.
- The endpoint is rate limited to 5 requests per minute per client IP.
- User input is escaped before being inserted into the HTML email template.
- Hidden docs reduce exposure in production unless `DEBUG=true`.

## Project Structure

```text
.
├── main.py
├── pyproject.toml
└── templates/
    └── email_template.html
```

## Development Notes

- The email template is stored in `templates/email_template.html`.
- SMTP connection uses STARTTLS and logs in before sending mail.
- The app currently exposes a single public form-submission endpoint.

## License

This project is licensed under the MIT License.

## Author

Kumar Sahil

- Email: krsahil8825@gmail.com
- GitHub: krsahil8825
