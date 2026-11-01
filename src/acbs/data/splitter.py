from __future__ import annotations

import numpy as np
from sklearn.model_selection import (
    KFold,
    ShuffleSplit,
    StratifiedKFold,
    StratifiedShuffleSplit,
    train_test_split,
)


def _class_min_count(y) -> int:
    """Smallest class population in ``y``; 0 when ``y`` is empty."""
    _, counts = np.unique(np.asarray(y), return_counts=True)
    return int(counts.min()) if counts.size else 0


def make_cv_splitter(
    *,
    y=None,
    cv_folds: int = 5,
    seed: int = 42,
) -> StratifiedKFold | StratifiedShuffleSplit | KFold | ShuffleSplit:
    """Build the outer-fold splitter shared by every contender.

    Adapts to class imbalance so stratified splits never crash on rare
    classes:

    * ``cv_folds <= 1`` -> one stratified holdout split.
    * smallest class >= ``cv_folds`` -> stratified ``cv_folds``-fold.
    * smallest class >= 2 but < ``cv_folds`` -> stratified folds reduced to
      the smallest class count.
    * any class with a single member -> non-stratified folds (stratification
      is impossible for singletons).
    """
    if cv_folds <= 1:
        return StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)

    cv_folds = int(cv_folds)
    if y is not None:
        min_count = _class_min_count(y)
        if min_count >= cv_folds:
            return StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
        if min_count >= 2:
            return StratifiedKFold(
                n_splits=min_count, shuffle=True, random_state=seed
            )
        return KFold(n_splits=cv_folds, shuffle=True, random_state=seed)

    return StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)


def make_holdout_split(X, y, *, test_size: float = 0.2, seed: int = 42):
    """Train/test split, stratified when every class has at least 2 members."""
    if _class_min_count(y) >= 2:
        return train_test_split(
            X, y, test_size=test_size, random_state=seed, stratify=y
        )
    return train_test_split(X, y, test_size=test_size, random_state=seed)


def identical_folds(
    splitter, X, y
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Materialise the split list once so all frameworks see identical folds."""
    return list(splitter.split(X, y))
