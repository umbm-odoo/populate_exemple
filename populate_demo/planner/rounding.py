"""Deterministic controlled rounding for quota tables.

The spec repeatedly needs a real-valued matrix (e.g. year x outcome, or
year x region) turned into whole-record counts that still sum exactly to
known row totals *and* known column totals (each already a whole number).
Rounding each cell independently can't guarantee both margins at once, so
this reconciles them with a plain, fully deterministic algorithm:

1. Floor every cell, then bring each row up to its exact target by handing
   the row's shortfall to the cells with the largest fractional remainder
   (largest-remainder method), tie-broken by column index.
2. That fixes every row total but can leave column totals off by a few
   units in either direction. Fix those by repeatedly moving a single unit,
   within one row, from a column that's currently over target to a column
   that's under target - choosing the row where that column's original
   remainder was least deserving of its rounding (for the "give a unit
   away" column) and most deserving (for the "receive a unit" column).

Row and column targets must already agree on the grand total; this module
does not invent or adjust either margin.
"""
from __future__ import annotations

from collections.abc import Sequence


def largest_remainder(values: Sequence[float], target: int) -> list[int]:
    """Round a single row of real values to integers summing to ``target``.

    Used where the spec only requires "largest-remainder rounding,
    reconciled within one order" for that one allocation (e.g. the
    geographic split for a single year) rather than a fixed column margin
    across every row - see ``reconcile_matrix`` for the latter.
    """
    floors = [int(v) for v in values]
    deficit = target - sum(floors)
    if deficit < 0:
        raise ValueError(f"Floors already exceed target {target}.")
    remainders = [v - int(v) for v in values]
    order = sorted(range(len(values)), key=lambda j: (-remainders[j], j))
    result = floors[:]
    for j in order[:deficit]:
        result[j] += 1
    return result


def reconcile_matrix(
    matrix: Sequence[Sequence[float]],
    row_targets: Sequence[int],
    col_targets: Sequence[int],
    forbidden: set[tuple[int, int]] | None = None,
) -> list[list[int]]:
    """Round ``matrix`` to whole numbers matching both ``row_targets`` and ``col_targets``.

    :param matrix: Real-valued cells, e.g. an exact 1% scaling of a spec table.
    :param row_targets: Exact integer sum required for each row.
    :param col_targets: Exact integer sum required for each column.
    :param forbidden: (row, col) cells that must stay exactly 0 (e.g. a region/warehouse
        combination that structurally can't happen, such as "other Europe" going through
        transit). Callers must ensure their matrix already has 0 there.
    :return: Whole-number matrix with the same shape, satisfying both margins exactly.
    :raise ValueError: If the margins are inconsistent (don't share a grand total),
        or the shape doesn't match the given targets.
    """
    n_rows, n_cols = len(matrix), len(matrix[0]) if matrix else 0
    if len(row_targets) != n_rows or any(len(row) != n_cols for row in matrix):
        raise ValueError("Matrix shape does not match row_targets.")
    if len(col_targets) != n_cols:
        raise ValueError("Matrix shape does not match col_targets.")
    if sum(row_targets) != sum(col_targets):
        raise ValueError(
            f"Row targets sum to {sum(row_targets)} but column targets sum to {sum(col_targets)}.",
        )
    forbidden = forbidden or set()
    if any(matrix[i][j] != 0 for i, j in forbidden):
        raise ValueError("A forbidden cell has a nonzero value in the input matrix.")

    remainders = [[cell - int(cell) for cell in row] for row in matrix]
    result = [[int(cell) for cell in row] for row in matrix]

    for i, row in enumerate(matrix):
        deficit = row_targets[i] - sum(result[i])
        if deficit < 0:
            raise ValueError(f"Row {i} floors already exceed its target {row_targets[i]}.")
        order = sorted(
            (j for j in range(n_cols) if (i, j) not in forbidden),
            key=lambda j: (-remainders[i][j], j),
        )
        for j in order[:deficit]:
            result[i][j] += 1

    def col_sum(j: int) -> int:
        return sum(result[i][j] for i in range(n_rows))

    col_errors = [col_sum(j) - col_targets[j] for j in range(n_cols)]

    # Local swaps: move one unit, within a single row, from an over-target
    # column to an under-target column. Always converges because each swap
    # strictly reduces total |error| by 2, and total error always sums to 0.
    max_swaps = n_rows * n_cols * 4
    for _ in range(max_swaps):
        if all(e == 0 for e in col_errors):
            break

        j_plus = max(range(n_cols), key=lambda j: col_errors[j])
        j_minus = min(range(n_cols), key=lambda j: col_errors[j])
        if col_errors[j_plus] <= 0 or col_errors[j_minus] >= 0:
            break  # shouldn't happen if margins agree, but avoid an infinite loop

        # Prefer rows where this column's value was actually rounded up (a
        # positive remainder) - taking a unit from a row whose cell was
        # already an exact integer is a less "deserved" correction, even
        # though the row's own total stays correct either way (the unit
        # moves to another column in the *same* row). Only fall back to an
        # exact cell when no rounded-up one is available, rather than
        # failing outright - with an unfavourable row/column shape (e.g. a
        # column forbidden in every row but the one already at its target)
        # every remaining candidate can legitimately have a zero remainder.
        def candidates(require_remainder: bool) -> list[int]:
            return [
                i for i in range(n_rows)
                if result[i][j_plus] > 0
                and (i, j_minus) not in forbidden
                and (not require_remainder or remainders[i][j_plus] > 1e-9)
            ]

        candidate_rows = candidates(True) or candidates(False)
        if not candidate_rows:
            raise ValueError(f"No row can give up a unit of column {j_plus} to reconcile totals.")
        row_i = min(
            candidate_rows,
            key=lambda i: (remainders[i][j_plus], -remainders[i][j_minus], i),
        )

        result[row_i][j_plus] -= 1
        result[row_i][j_minus] += 1
        col_errors[j_plus] -= 1
        col_errors[j_minus] += 1
    else:
        raise ValueError("Could not reconcile column totals within the expected number of swaps.")

    return result
