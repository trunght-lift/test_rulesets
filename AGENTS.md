# Repository rules

- Review with production safety first.
- Never allow pushes that introduce obvious correctness bugs.
- Treat missing tests for payment/auth changes as blocking unless the diff is clearly non-functional.
- Flag security issues, unsafe null handling, weak error handling, and risky logging as blocking.
- Prefer concise findings. Ignore cosmetic nits unless they are truly risky.
