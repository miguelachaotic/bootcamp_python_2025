from itertools import pairwise
import pytest
from copy import deepcopy
import numpy as np

def remove_duplicates(values: list[int]) -> int:
    j = 1
    for i in range(1, len(values)):
        if values[i] != values[i-1]:
            values[j] = values[i]
            j += 1
    return j
        

@pytest.mark.parametrize(
    'values, expected_output, expected_values',
    [
        ([1, 2, 3], 3, [1, 2, 3]),
        ([1, 1, 1], 1, [1, 1, 1]),
        ([1, 4, 5], 3, [1, 4, 5]),
        ([1, 2, 2, 3, 3, 7], 4, [1, 2, 3, 7, 3, 7]),
        ([-2, 1, 1, 5, 8, 9, 9, 9, 9, 9, 9], 5, [-2, 1, 5, 8, 9, 9, 9, 9, 9, 9, 9])
    ]
)
def test_remove_duplicates(values, expected_output, expected_values):
    copy_values = deepcopy(values)
    assert remove_duplicates(values) == expected_output
    assert values == expected_values
    assert list(np.unique(copy_values)) == expected_values[:expected_output]
