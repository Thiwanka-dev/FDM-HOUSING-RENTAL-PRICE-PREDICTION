# Setup guide

How to run the project on your own computer after cloning it: the notebooks,
the saved models, the Python backend and the React website.

The commands are for Windows. On macOS or Linux, activate the virtual
environment with `source .venv/bin/activate` instead.

## What you need installed

| Tool | Version | Check with |
|---|---|---|
| Git | any | `git --version` |
| Python | 3.13 | `python --version` |
| Node.js | 20.19 or newer | `node --version` |

## Step 1: Clone the repository

```
git clone https://github.com/Thiwanka-dev/FDM-HOUSING-RENTAL-PRICE-PREDICTION.git
cd FDM-HOUSING-RENTAL-PRICE-PREDICTION
```

Run every command below from this project folder, unless a step says otherwise.

## Step 2: Create the Python environment

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

`requirements.txt` installs the GPU build of PyTorch, which is a download of
several gigabytes. It also runs on a computer without an NVIDIA GPU.

Activate the environment (`.venv\Scripts\activate`) again in every new terminal.

## Step 3: Add the data

The CSV files are too large for git, so each person adds them.

1. Download the USA Housing Listings dataset (Kaggle) and save it as
   `data/housing.csv`.
2. Open `notebooks/02_Preprocessing.ipynb` and run all cells.

The notebook creates four files in the `data` folder: `raw_train.csv`,
`raw_test.csv`, `train.csv` and `test.csv`.

## Step 4: Create the Random Forest model

Three of the four saved models are stored in git. The Random Forest file is
about 270 MB, which is above GitHub's limit, so it is trained on your computer:

```
python -m models.setup_models --evaluate-test
```

This takes about one minute. It trains the Random Forest, then scores all four
models on the test set. The result should be:

| Model | Test MAE | Test R² |
|---|---|---|
| Neural Network | 149.48 | 0.8293 |
| Random Forest | 161.40 | 0.7943 |
| Gradient Boosting | 229.54 | 0.6710 |
| Ridge Regression | 242.01 | 0.6399 |

## Step 5: Start the backend

```
uvicorn backend.app.main:app --reload
```

Leave this terminal open. To check that it works, open
http://127.0.0.1:8000/docs in a browser. It shows the API endpoints and lets
you try them.

## Step 6: Start the website

Open a second terminal in the project folder:

```
cd frontend
npm install
npm run dev
```

`npm install` is only needed the first time. Then open http://localhost:5173
in a browser. The backend from Step 5 must still be running.

## Step 7: Run the tests (optional)

In a terminal with the virtual environment active:

```
python -m pytest backend
```

All tests should pass. Tests that need a missing file are reported as skipped.

## If you only want to run the website

Steps 3 and 4 can be skipped. The backend then runs with the Neural Network,
Gradient Boosting and Ridge Regression models. The Random Forest is shown as
unavailable until Step 4 is done.

## Problems and fixes

| Problem | Cause and fix |
|---|---|
| `{"detail":"The Random Forest model file is missing..."}` | Step 4 was skipped. Run `python -m models.setup_models`. |
| `Missing data files: data\raw_train.csv` | Step 3 was skipped. Add `housing.csv` and run `02_Preprocessing.ipynb`. |
| `ModuleNotFoundError: No module named 'backend'` or `'models'` | The command was run from the wrong folder. Run it from the project folder, not from `backend` or `frontend`. |
| `No module named 'fastapi'` or `'uvicorn'` | The virtual environment is not active, or `pip install -r backend/requirements.txt` was skipped. |
| The website shows "The backend is not running" | Start the backend (Step 5) and reload the page. |
| `npm install` hangs or fails with `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | The network's firewall is inspecting the connection to the npm registry. Use another network, such as a home connection or a mobile hotspot. |
| The map on the website is grey or empty | The map images are downloaded from OpenStreetMap, so the computer needs an internet connection. The state and region lists work without it. |
| `Port 8000 is already in use` | Another backend is already running. Close it, or use that one. |
