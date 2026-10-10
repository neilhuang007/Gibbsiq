# Model conventions

These equations define the sign and counting conventions used by Gibbsiq's
discrete models and bundled evaluation fixtures.

## Ising energy

For spins `s_i` in `{-1, +1}`, the energy is

```text
E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j.
```

Each interaction appears once. Positive `J_ij` favors opposite spins; negative
`J_ij` favors equal spins. Constant offsets affect reported energies even when
they cancel from normalized probabilities.

## Binary to spin mapping

For a binary variable `x_i` in `{0, 1}`, use `s_i = 2*x_i - 1`, or equivalently
`x_i = (s_i + 1)/2`.

## QUBO conversion

Write a QUBO as `c + sum_i a_i x_i + sum_{i<j} b_ij x_i x_j`.
Substitution gives

```text
J_ij = b_ij / 4
h_i = a_i / 2 + sum_{j != i} b_ij / 4
offset = c + sum_i a_i / 2 + sum_{i<j} b_ij / 4.
```

Here `b_ij` in the field sum denotes the single stored coefficient for the
unordered pair. Binary diagonal terms are linear because `x_i*x_i = x_i`;
spin diagonal terms are constant because `s_i*s_i = 1`.

## Boltzmann probability

At inverse temperature `beta >= 0`,
`P(s) = exp(-beta*E(s)) / sum_t exp(-beta*E(t))`.
At `beta = 0`, all states have equal probability. Exact enumeration is bounded
to small models because the number of states grows exponentially.

## Gibbs conditional

Given the other spins, let `field_i = h_i + sum_{j != i} J_ij*s_j`.
Then `P(s_i = +1 | s_-i) = 1 / (1 + exp(2*beta*field_i))`.
The positive energy sign in this convention determines the sign of the exponent.

## Max-Cut

For an unweighted graph, set `J_ij = 1` on each edge, zero fields, and zero
offset. Each cut edge has opposite spins, so
`cut_size = (number_of_edges - E(s))/2`.

The generated optimization corpus cites
[Lucas's Ising formulations](https://doi.org/10.3389/fphy.2014.00005) for its
problem encodings. Its tiny-instance optima are computed by exhaustive
enumeration and checked separately from the candidate evaluator.
