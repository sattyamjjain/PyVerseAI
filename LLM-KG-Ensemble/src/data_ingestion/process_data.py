import pandas as pd


def clean_data(file_path):
    df = pd.read_csv(file_path)
    # Clean the data: drop missing values, normalize columns, etc.
    df = df.dropna(subset=["name", "country"])
    df["sector"] = df["sector"].fillna("Unknown")

    return df


if __name__ == "__main__":
    processed_df = clean_data("../../data/raw/world_bank_projects.csv")
    processed_df.to_csv(
        "../../data/processed/cleaned_world_bank_projects.csv", index=False
    )
    print("Data cleaned and saved to cleaned_world_bank_projects.csv")
