# Machine Learning-Based U.S. Residential Rental Price Estimation System

IT3051 Fundamentals of Data Mining project.

## Local setup

Run every command from the project folder.

1. Create and activate a virtual environment (Python 3.13):

   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install the dependencies. `requirements.txt` installs the GPU build of
   PyTorch; it also runs on a computer without an NVIDIA GPU.

   ```
   pip install -r requirements.txt
   ```

3. Add the data. The CSV files are not stored in git. Place the USA Housing
   Listings dataset as `data/housing.csv`, then run
   `notebooks/02_Preprocessing.ipynb`. It creates `raw_train.csv`,
   `raw_test.csv`, `train.csv` and `test.csv` in the `data` folder.

4. Create the model files that are not stored in git:

   ```
   python -m models.setup_models --evaluate-test
   ```

   The Neural Network, Gradient Boosting and Ridge Regression files are in the
   repository. The Random Forest file (about 270 MB) is too large for GitHub,
   so this command trains it (about one minute). `--evaluate-test` then scores
   all four saved models on `raw_test.csv`.

## Models

| Model | Notebook | Saved model | Test MAE | Test R² |
|---|---|---|---|---|
| Ridge Regression | `03_Linear_Ridge_Models.ipynb` | `models/linear_ridge/artifacts/linear_ridge.joblib` | $242.01 | 0.6399 |
| Random Forest | `03_RandomForest_Thiwanka.ipynb` | `models/random_forest/artifacts/random_forest.joblib` (built by setup) | $161.40 | 0.7943 |
| Gradient Boosting | `04_GradientBoosting_Janeesha.ipynb` | `models/gradient_boosting/artifacts/gradient_boosting.joblib` | $229.54 | 0.6710 |
| **Neural Network (selected)** | `04_NeuralNetwork_Savindu.ipynb` | `models/neural_network/artifacts/neural_network.pt` | **$149.48** | **0.8293** |

`notebooks/05_Model_Comparison.ipynb` compares the four models on the same
test set and selects the Neural Network as the final model.
