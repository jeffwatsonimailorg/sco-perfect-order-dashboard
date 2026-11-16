# Databricks notebook source
from sklearn.model_selection import train_test_split


def get_data_splits(X, y, train_size=0.7):
    """Generate balanced data splits."""
    X_train, X_, y_train, y_ = train_test_split(
        X, y, train_size=train_size, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_, y_, train_size=0.5, stratify=y_
    )
    return X_train, X_val, X_test, y_train, y_val, y_test
