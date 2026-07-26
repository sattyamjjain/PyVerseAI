from typing import Iterable, Callable

import pandas as pd


def accuracy(preds: Iterable, targets: Iterable) -> float:
    """
    Computes the accuracy (percentage of matching strings) between two iterables.
    Args:
        preds (Iterable[str]): Predicted values.
        targets (Iterable[str]): Target values.
    Returns:
        float: Accuracy as a percentage.
    """
    preds = list(preds)
    targets = list(targets)
    if len(preds) != len(targets):
        raise ValueError("Input iterables must have the same length.")
    matches = sum(p == t for p, t in zip(preds, targets))
    return matches / len(preds) if preds else 0.0


def evaluate_product_prediction(data: pd.DataFrame, predict_product_id: Callable[[pd.DataFrame], Iterable[str]]) -> float:
    """
    Applies a function to the DataFrame and computes accuracy against the 'product_id' column.

    Args:
        data (pd.DataFrame): Input DataFrame.
        predict (Callable): Function to apply to the DataFrame. Should return an iterable of predicted product_ids.

    Returns:
        float: Accuracy as a percentage.
    """
    preds = predict_product_id(data[['requirement', 'requirement_detail']])
    targets = data['product_id']
    return accuracy(preds, targets)
