# Data Challenge: Product Matching System

> **Solution:** see [SOLUTION.md](SOLUTION.md) for the implemented approaches, evaluation
> methodology and results. Experiments live in `experiments/`, the deliverable functions in
> `src/tasks.py`, and `scripts/run_eval.py` reproduces every number.

## Problem Description

This challenge involves developing a product matching system for a manufacturer of sanitary products (toilets, etc.). The manufacturer frequently receives requests from construction projects inquiring about products that meet specific requirements. The challenge is to develop 1 to 3 algorithms that can match these requirements to the appropriate products in the manufacturer's catalog.

The data consists of two main components:
- `data/products.csv`: Contains the manufacturer's product catalog with detailed descriptions. This file has the following columns:
  - `product_id`: A unique identifier for each product.
  - `name`: The name of the product, includes some key properties.
  - `description`: A description of the product, outlining its properties.
  - `category`: The product’s category (less critical).
- `data/requirements.csv`: Contains labeled data where requirements are matched with their corresponding product IDs. This file has the following columns:
  - `requirement`: A short description of the requirement as received.
  - `requirement_detail`: A more detailed explanation of the requirement.
  - `product_id`: The ID of the product historically selected for this requirement, matching `data/products.csv`’s `product_id`.
In practice, only `requirement` and `requirement_detail` are available to the manufacturer; The `product_id` needs to be selected by them based on the requirement data and product catalog.

The goal is to implement an algorithm that can accurately match requirement text to specific products, helping the manufacturer efficiently respond to construction project inquiries.

## Code Structure

The codebase is organized as follows:

### Data Loading (`src/load_data.py`)
- Contains helper functions to load the product and requirements data
- `load_products()`: Loads the product catalog
- `load_requirements()`: Loads the requirements dataset

### Task Implementation (`src/tasks.py`)
- Contains the main deliverable: `predict_product_id(df: pd.DataFrame) -> Iterable[str]`
- This function should match requirements to product IDs
- It takes in a dataframe with the same structure as `requirements.csv` without the `product_id` column and returns `list` of matching product_ids in the same order as the entries in the dataframe
- Designed to work with any requirement data, not just the provided dataset

### Evaluation (`src/evaluate.py`)
- Provides helper functions for evaluating the matching algorithm
- Includes an accuracy metric
- Can be used to assess the performance of different matching approaches
- `evaluate_product_prediction(data: pd.DataFrame, predict_product_id: Callable[[pd.DataFrame], Iterable[str]]) -> float`: Takes in the full `requirements.csv` dataframe as well as the `predict_product_id` function, returns the accuracy of matching on the dataset.

### Visualization (`visualization/`)
- Contains Jupyter notebooks for data exploration and visualization:
  - `products.ipynb`: Visualization of the product dexcriptions
  - `requirements.ipynb`: Visualization of the requirements (texts)

## Tasks

1. **Data Analysis and Preprocessing**
   - Examine and understand the data structure
   - Clean and preprocess the data as needed
   - Potentially identify patterns and relationships between requirements and products
   - This should not be the main focus

2. **Algorithm Development**
   - Experiment with and implement 1 to 3 method(s) to predict product IDs from requirements
   - Consider various approaches
   - Think about the reasoning behind (the) chosen approach(es)
   - You can experiment with methods e.g. in jupyter notebooks

3. **Evaluation Framework**
   - If helpful, develop appropriate metrics to evaluate the matching methods
   - Implement evaluation procedures
   - Compare different approaches

4. **Implementation**
   - Implement the `predict_product_id` function (or multiple functions with this signature - one for each method)
   - Ensure it works with the specified input format (DataFrame with 'requirement' and 'requirement_detail' columns)

5. **Analysis and Documentation**
   - Compare different approaches. You do not need to implement all of them, you just need to be able to talk about them
   - Think about advantages and disadvantages
   - Run all code even if incomplete or unoptimized and document evaluation results

## Additional Notes

- **Partial Coverage**: It's acceptable if the algorithm only works for a subset of products. Consider how to extend it to handle all cases.

- **Multiple Approaches**: Consider various approaches to solve the problem:
  They do not necessarily need to be data-driven. Keep in mind the reasoning behind your chosen approach(es). This is an open-ended problem. Be arbitrarily creative in your approaches.

- **Realistic Expectations**: This is a challenging problem. The focus is on:
  - Approach development
  - Implementation capability
  - Evaluation methodology
  The solution doesn't need to be perfect. We care about how you approach this problem, which methods you come up with and how you go about iterating on them.

- **Tools and Resources**:
  - You may use any tools (ChatGPT, Cursor, etc.)
  - Any libraries can be used
  - An OPENAI_API_KEY is provided for working with OpenAI models

- **Documentation**:
  - Document all approaches and experiments (do not delete any code you wrote)
  - Use .py or .ipynb files for documentation
  - Keep experimental code for review
  - Only the final `predict_product_id` function should be clean, experiments can be written in jupyter notebooks and can be arbitrarily messy
