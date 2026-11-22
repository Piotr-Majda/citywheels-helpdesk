# CityWheels help desk — v0.1.0

**Version:** [v0.1.0](https://github.com/Piotr-Majda/citywheels-helpdesk/tree/v0.1.0)
· **Offline tests:** 118 passed
· **Real-model evaluation:** 8/10 plus 3/5 additional cases

CityWheels is a made-up bike rental shop. This repository contains its Python CLI
help desk agent and the original sample data described below.

## Run the agent, tests, and evaluation

Requires Python 3.14+, uv, and a running Ollama instance with `llama3.1:8b` installed.

```bash
uv sync --locked
uv run python -m app.main "How much will I get back for CW-1002?"
uv run pytest
uv run python -m eval.run
```

Start with [INSTALL.md](INSTALL.md) for a fresh clone and setup. See
[SOLUTION.md](SOLUTION.md) for the current architecture, decisions, and limitations.
The [release evaluation manifest](eval/RELEASE.md) binds the saved reports to this
version; [fresh-checkout verification](docs/VERIFICATION.md) records the setup check.
The [evaluation guide](eval/README.md) explains checks and limits; the
[latest real-model results](eval/results.md) include answers, tool traces, and timings.

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
