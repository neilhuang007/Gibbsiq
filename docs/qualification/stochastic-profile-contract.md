# Stochastic profiles

A profile specifies how numerical values become stochastic computations.
Its identity includes encoding, transition law, readout, and randomization.

## Ideal IID tanh

For field `x`, the output spin is +1 with probability
`(1 + tanh(x)) / 2`. Averaging independent spins estimates `tanh(x)`.
The profile records the number of draws and assigns deterministic random
streams to runs and operations.

Whole-model sampling uses this profile at named Z1T projections. The remaining
model computation follows the numerical traversal.

## Four-parent dy4p

The local dy4p profile encodes a scalar with four spin weights:
1/4, 1/8, 1/16, and 1/32. Its 16 codewords span -15/32 through +15/32.

Nearest-codeword encoding uses ties-to-even rounding. Saturating and rejecting
encoders have distinct identities. The reference enumerates the parent-spin
law and conditional output distribution. Parent resampling and shared-parent
execution are explicit choices.

## Reference comparisons

Use the numerical reference to assess the complete approximation. Use the
representation reference to isolate sampling error after encoding. Named
profiles keep those comparisons reproducible across experiments.

Core profile definitions live in `qualification.profiles`; model execution
uses `qualification.adapters.z1t_emulation`.
