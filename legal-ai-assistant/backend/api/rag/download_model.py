# download_model.py

from sentence_transformers import SentenceTransformer
import os

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
# Define the local directory path where the model will be saved
LOCAL_MODEL_PATH = './local_models/all-MiniLM-L6-v2' 

def download_and_save_model():
    """Downloads the Sentence Transformer model and saves it locally."""
    print(f"Starting download for model: {MODEL_NAME}")
    print(f"Saving to directory: {LOCAL_MODEL_PATH}")

    # Ensure the directory exists
    os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)
    
    try:
        # Load the model from Hugging Face (requires internet)
        model = SentenceTransformer(MODEL_NAME)
        
        # Save all model files locally
        model.save(LOCAL_MODEL_PATH)
        
        print("\n✅ Download and save complete!")
        print("You can now copy the entire 'local_models' folder to your offline environment.")

    except Exception as e:
        print(f"\n❌ Error during model download: {e}")
        print("Please check your internet connection and try again.")


if __name__ == "__main__":
    download_and_save_model()

# Run this script:
# python download_model.py