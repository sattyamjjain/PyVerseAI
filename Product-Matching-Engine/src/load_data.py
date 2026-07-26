import os
import pandas as pd

def get_data_path(filename):
    """Return the absolute path to a file in the dat folder."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dat_dir = os.path.join(base_dir, 'data')
    return os.path.join(dat_dir, filename)

def load_products():
    """Load products data from the dat folder."""
    path = get_data_path('products.csv')
    return pd.read_csv(path)

def load_requirements():
    """Load requirements data from the dat folder."""
    path = get_data_path('requirements.csv')
    return pd.read_csv(path)
