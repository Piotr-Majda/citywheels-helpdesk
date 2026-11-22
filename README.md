# CityWheels help desk

**Historical release:** [v0.1.0](https://github.com/Piotr-Majda/citywheels-helpdesk/tree/v0.1.0)
· **Offline tests:** 118 passed
· **Real-model evaluation:** 8/10 plus 3/5 additional cases

CityWheels is a made-up bike rental shop. This repository contains its Python CLI
help desk agent and the original sample data described below.

**Docker option:** [DOCKER.md](DOCKER.md) describes Compose setup for
an online OpenAI provider or an optional self-hosted Ollama service. Container
verification: 151 offline tests passed; live provider execution through Docker
is not yet verified. The v0.1.0 release results above remain historical.

The current `main` checkout also loads a root `.env` automatically using
Pydantic Settings and avoids staff-contact footers for ordinary policy answers.
Its native offline suite passes **151 tests**. The saved OpenAI `gpt-5.4-nano`
run passes **10/10**, with a median of **2.320 seconds** per case, compared with
Ollama's current **7/10** and **19.084 seconds** on the same application. See the
[model reference comparison](eval/reference/README.md) for both reports and the
compatibility checks and failure analysis. The v0.1.0 results above remain historical.

## Run the agent, tests, and evaluation

Requires Python 3.14+ and uv. Configure OpenAI in `.env`, or use a running Ollama
instance with `llama3.1:8b` installed. See [INSTALL.md](INSTALL.md) for both paths.

```bash
uv sync --locked
uv run python -m app.main "How much will I get back for CW-1002?"
uv run pytest
uv run python -m eval.run --output eval/local-run/review
```

Start with [INSTALL.md](INSTALL.md) for a fresh clone and setup. See
[SOLUTION.md](SOLUTION.md) for the current architecture, decisions, and limitations.
The [release evaluation manifest](eval/RELEASE.md) binds the saved reports to this
version; [fresh-checkout verification](docs/VERIFICATION.md) records the setup check.
The [evaluation guide](eval/README.md) explains checks and limits; the
[current model references](eval/reference/README.md) include answers, tool traces, and timings.

## Files

| File | What it holds |
| --- | --- |
| `data/policies/prices.md` | Bike types, rental prices, add-ons, deposits and late return fees. |
| `data/policies/cancellations.md` | Rules for cancelling or changing a booking, and for refunds. |
| `data/policies/faq.md` | Answers to common questions: opening hours, age limits, payment, what to do when something goes wrong. |
| `data/bookings.json` | Example bookings. |

## Bookings

Each booking in `data/bookings.json` has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Booking number, for example `CW-1001`. |
| `status` | `confirmed`, `in_progress`, `completed` or `cancelled`. |
| `bike_type` | `city`, `e-bike` or `kids`. |
| `bikes` | How many bikes are booked. |
| `start`, `end` | When the rental starts and ends, with the time zone. |
| `add_ons` | Extras, such as `child_seat`. |
| `rental_price_eur` | Price of the rental itself, with add-ons. |
| `booking_fee_eur` | Fee for booking online. |
| `deposit_eur` | Deposit paid with the booking. |
| `paid_with` | `card` or `voucher`. |

## The current date

The bookings are set in June 2026. So that answers are the same every time, treat the current date and time as:

**2026-06-10 09:00, Europe/Warsaw time (UTC+02:00).**

## Example questions

- What time do you open on Saturday?
- How much is an e-bike for a whole day?
- I want to cancel booking CW-1002. How much will I get back?
- Can my 14-year-old rent an e-bike?
- What is the capital of Australia?
