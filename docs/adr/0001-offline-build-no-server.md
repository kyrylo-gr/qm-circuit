# Build programs offline; never reach a Quantum Machines server

The library uses the `qm-qua` package only to build the QUA program in memory, and never creates a `QuantumMachinesManager`, compiles, simulates or runs a job. The diagram must not be able to write to, start or disturb an experiment, so the package stays isolated from the server by design, even though server-side compilation and simulation would give exact timings and waveforms for free.

## Consequences

- No configuration is available, so pulse lengths and config values are unknown: the horizontal axis is statement order, not time, and only explicit parameters are shown.
- Anything that needs the server (waveform reports, timing checks, config validation) stays out of scope. A feature that needs it is a new decision, not a gap.
