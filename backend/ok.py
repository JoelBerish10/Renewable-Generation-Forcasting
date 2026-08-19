import os
import joblib

script_dir = os.path.dirname(os.path.abspath(__file__))
test_path = os.path.join(script_dir, "test.pkl")

joblib.dump({"test": 123}, test_path)

if os.path.exists(test_path):
  print(f"File system working! Created: {test_path}")