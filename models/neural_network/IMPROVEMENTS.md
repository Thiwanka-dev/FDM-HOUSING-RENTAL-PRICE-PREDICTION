# Neural Network: Findings and Possible Improvements

This note records what was learned while building the neural network in
`notebooks/04_NeuralNetwork_Savindu.ipynb`, and the improvements that were
identified but not implemented because of time. It is written so that the work
can be picked up later without re-running the experiments.

Written on 3 October 2026. All figures are in dollars of monthly rent.

## 1. Where the model stands

The selected model is `Tuned_5` in the notebook:

- Embeddings for the five categorical features (`region`, `type`, `state`,
  `laundry_options`, `parking_options`).
- Periodic (Fourier) features for latitude and longitude: 32 learnable
  frequencies per coordinate, initialised with a standard deviation of 30.
- Three hidden layers (1024, 512, 256) with batch normalisation, ReLU and a
  dropout rate of 0.3.
- Huber loss on the standardised `log1p(price)`, AdamW (learning rate 0.001,
  weight decay 0.0001), batch size 512, learning rate halved after 3 epochs
  without improvement, early stopping after 10.

| Evaluation | MAE | RMSE | R² |
|---|---|---|---|
| Validation set (15% of the training data) | 151.62 | 276.39 | 0.8280 |
| 3-fold cross-validation (mean) | 163.27 | 293.00 | 0.8105 |
| Random Forest, tuned, same 3 folds | 172.01 | 316.11 | 0.7794 |

The validation figure is slightly optimistic, because the validation set was
used both for early stopping and for choosing the configuration. The
cross-validation figure is the more realistic one.

## 2. Findings

### 2.1 How location is represented matters more than anything else

Adding periodic features for latitude and longitude reduced the validation MAE
from 189 to 160 with the same layers as the baseline. Nothing else came close.
Rent changes sharply between neighbourhoods, and a network that receives the
plain standardised coordinates only learns the broad geographic trend.

### 2.2 Standard tuning has almost no effect without the periodic features

Validation results for the baseline architecture (256, 128, 64) and variations
of it, all without periodic features:

| Configuration | Valid MAE | Valid R² |
|---|---|---|
| Baseline (dropout 0.1) | 189.1 | 0.762 |
| Dropout 0.3 | 192.3 | 0.755 |
| Dropout 0.2, weight decay 0.001 | 190.6 | 0.759 |
| Batch size 256 | 190.5 | 0.760 |
| Batch size 1024, learning rate 0.002 | 189.5 | 0.757 |
| 512-256-128, dropout 0.2 | 187.5 | 0.761 |
| 1024-512-256, dropout 0.3 | 186.6 | 0.764 |
| 1024-512-256, dropout 0.1 | 187.8 | 0.759 |
| 512-512-512-512, dropout 0.2 | 186.2 | 0.762 |

### 2.3 Settings of the periodic features

Baseline architecture (256, 128, 64) with periodic features on `lat` and
`long`. "Sigma" is the standard deviation used to initialise the frequencies.

| Frequencies | Sigma | Valid MAE | Valid R² |
|---|---|---|---|
| 16 | 1 | 178.8 | 0.783 |
| 32 | 3 | 167.4 | 0.806 |
| 16 | 10 | 161.9 | 0.814 |
| 32 | 10 | 161.1 | 0.815 |
| 32 | 20 | 160.0 | 0.815 |
| 32 | 30 | 159.3 | 0.815 |
| 32 | 50 | 160.8 | 0.817 |
| 32 | 100 | 160.3 | 0.816 |
| 64 | 10 | 158.5 | 0.822 |
| 64 | 30 | 157.0 | 0.820 |

- Sigma must be at least about 10. Above that the result is flat.
- 64 frequencies were slightly better than 32. This was not carried into the
  notebook and is the first thing to try (see 3.2).
- Applying the periodic features to `sqfeet` as well made the result worse
  (MAE 170.3 with 32 frequencies and sigma 10, against 161.1 for the
  coordinates alone).

### 2.4 With the periodic features, larger networks help

| Hidden layers | Dropout | Sigma | Valid MAE | Valid R² |
|---|---|---|---|---|
| 256-128-64 | 0.1 | 30 | 160.3 | 0.816 |
| 256-128-64 | 0.2 | 10 | 161.3 | 0.818 |
| 512-256-128 | 0.2 | 30 | 154.3 | 0.822 |
| 1024-512-256 | 0.3 | 30 | 151.6 | 0.828 |

The trend had not flattened at the largest size tested. The first row differs
by about 1 from the same setting in 2.3 because the two runs started from
different random weights; differences of that size are noise.

### 2.5 The model fits the training data much more closely than unseen data

For `Tuned_5` the training MAE is 86 against a validation MAE of 152. The
network memorises local price levels in detail. Higher dropout narrowed this
gap in the experiments but did not improve the validation error.

### 2.6 Data issues that remain in the training set

- 213 training listings (0.17%) have a price below 100, and the cheapest cost
  1. They are kept, and the Huber loss limits their influence.
- `sqfeet` ranges from 1 to 1,019,856 in the raw data. It is clipped to the
  0.5th and 99.5th percentiles (about 208 to 3,160) before the log transform.
- 37 training listings have coordinates outside the United States. They are
  clipped to the 0.1st and 99.9th percentiles.

## 3. Improvements, in order of expected benefit

The expected gains are estimates, not measurements. Together they might move
the cross-validation MAE from 163 to roughly 153-158.

### 3.1 Five-fold ensemble (largest and most dependable gain)

Train five networks, each on a different 80% of the training data with the
remaining 20% used for early stopping, and average their predictions.

- Averaging reduces the error of the individual networks.
- Together the five networks learn from all the training data. At present 15%
  is held out for early stopping and never used for learning.
- The same five runs give a 5-fold cross-validation estimate.

How: reuse `RentalPreprocessor`, `build_model` and `train_model` from the
notebook inside a `KFold(n_splits=5)` loop, keep the five models and their
preprocessors, and average the dollar predictions on the test set.
Expected gain 2-4%. About 25 minutes.

Note: the fold-by-fold comparison with the Random Forest (3 folds) is then no
longer possible. The comparison on the test set remains valid.

### 3.2 Wider search of the settings that mattered

Only six configurations were compared in the notebook. Worth trying:

- 64 frequencies instead of 32 (see 2.3).
- Wider or deeper networks than 1024-512-256 (see 2.4).
- Learning rate, weight decay and batch size for the large network. These
  were only tested on the small baseline.
- A patience above 10 for early stopping.

A random search over 20-30 configurations is enough. Expected gain 1-3%.
About 50 minutes of training.

### 3.3 Remove implausible listings from the training data only

Drop the training listings with a price below 100 before fitting. The
validation and test sets must stay unchanged. Small or no gain. About 10
minutes.

### 3.4 Simple engineered features

For example square feet per bedroom and bathrooms per bedroom. Small or no
gain. About 15 minutes.

## 4. Ideas that were set aside

- **Neighbour-price features** (the average rent of the nearest training
  listings). Possibly the largest gain of all, because many listings share a
  building or a street. It must be computed out-of-fold to avoid leaking the
  target, which is easy to get wrong, and it adds at least an hour.
- **Transformer architectures for tabular data** (for example FT-Transformer).
  Much slower to train, with uncertain benefit on this dataset.
- **5-fold instead of 3-fold cross-validation on its own.** It does not change
  the model. It only gives a slightly tighter estimate, and it breaks the
  comparison with the Random Forest.

## 5. Rules to keep when making changes

- Fit every preprocessing step on the training rows only.
- Choose configurations on the validation set or by cross-validation, never
  on the test set.
- Evaluate on `raw_test.csv` once, at the end. The other models in the project
  are scored on the same 35,920 listings.
