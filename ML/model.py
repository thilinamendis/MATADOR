import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier  # Example model
import pickle

# Load the training data
data = np.load("training_data.npy", allow_pickle=True)
X = np.array([item[0] for item in data])
y = np.array([item[1] for item in data])

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train a simple Random Forest classifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save the model
with open("tampering_model.pkl", "wb") as f:
    pickle.dump(model, f)
print("Model trained and saved to tampering_model.pkl")
