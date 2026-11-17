import tensorflow as tf
import numpy as np
import os

# Suppress TensorFlow terminal spam
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

# Load the model globally so it only initializes once
try:
    model = tf.keras.models.load_model('unwanted_image_model.keras')
    print("MobileNetV3 Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def is_unwanted_image(image_path):
    """Evaluates an image and returns True if it should be quarantined."""
    if model is None:
        return False
        
    try:
        # Resize the image to 224x224, strictly required by MobileNetV3
        img = tf.keras.utils.load_img(image_path, target_size=(224, 224))
        
        # Convert to array and add a batch dimension
        img_array = tf.keras.utils.img_to_array(img)
        img_array = tf.expand_dims(img_array, 0)
        
        # Run the prediction
        predictions = model.predict(img_array, verbose=0)
        score = tf.nn.softmax(predictions[0])
        predicted_class = np.argmax(score)
        
        # Keras sorts folders alphanumerically: 'Delete' comes before 'Keep'.
        # Therefore, Class 0 = Delete, Class 1 = Keep.
        if predicted_class == 0:
            print(f"[AI Scanner] Unwanted image detected: {image_path.name} (Confidence: {100 * np.max(score):.2f}%)")
            return True
            
        return False
        
    except Exception as e:
        print(f"Failed to scan {image_path.name}: {e}")
        return False