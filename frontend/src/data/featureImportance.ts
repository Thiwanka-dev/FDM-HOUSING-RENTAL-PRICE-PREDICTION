// Permutation importance of the Neural Network, copied from section 7.6 of
// notebooks/04_NeuralNetwork_Savindu.ipynb: the increase in validation MAE
// (in dollars) when the values of one feature are shuffled.

export const FEATURE_IMPORTANCE: { feature: string; maeIncrease: number }[] = [
  { feature: 'Longitude', maeIncrease: 168.53 },
  { feature: 'Region', maeIncrease: 129.61 },
  { feature: 'Size (square feet)', maeIncrease: 97.72 },
  { feature: 'Latitude', maeIncrease: 86.98 },
  { feature: 'State', maeIncrease: 52.64 },
  { feature: 'Laundry', maeIncrease: 41.96 },
  { feature: 'Property type', maeIncrease: 29.2 },
  { feature: 'Parking', maeIncrease: 25.73 },
  { feature: 'Bedrooms', maeIncrease: 24.85 },
  { feature: 'Bathrooms', maeIncrease: 14.94 },
  { feature: 'Smoking allowed', maeIncrease: 9.26 },
  { feature: 'Furnished', maeIncrease: 7.8 },
  { feature: 'Dogs allowed', maeIncrease: 4.67 },
  { feature: 'Cats allowed', maeIncrease: 3.9 },
  { feature: 'Wheelchair access', maeIncrease: 3.0 },
  { feature: 'Electric vehicle charging', maeIncrease: 1.01 },
]
