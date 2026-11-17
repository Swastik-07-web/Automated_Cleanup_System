import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV3Small

batch_size = 32
# MobileNetV3 requires 224x224 image dimensions
img_height = 224 
img_width = 224

# Your local dataset location
data_dir = "C:/Users/chakr/SmartCleanup_Project/blurdataset"

print("Loading training data...")
train_ds = tf.keras.utils.image_dataset_from_directory(
    data_dir, validation_split=0.2, subset="training", seed=123,
    image_size=(img_height, img_width), batch_size=batch_size)

print("Loading validation data...")
val_ds = tf.keras.utils.image_dataset_from_directory(
    data_dir, validation_split=0.2, subset="validation", seed=123,
    image_size=(img_height, img_width), batch_size=batch_size)

AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# Load the MobileNetV3 base and freeze its pre-trained weights
base_model = MobileNetV3Small(input_shape=(img_height, img_width, 3), 
                              include_top=False, weights='imagenet')
base_model.trainable = False 

# Attach your custom classification layers
model = models.Sequential([
    layers.Rescaling(1./255, input_shape=(img_height, img_width, 3)),
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation='relu'),
    layers.Dense(2) # 2 classes: Keep vs Delete
])

model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

print("Starting training...")
model.fit(train_ds, validation_data=val_ds, epochs=5)

# Save directly to the same folder where your daemon.py is located
model.save('C:/Users/chakr/SmartCleanup_Project/unwanted_image_model.keras')
print("Model trained and saved directly to SmartCleanup_Project!")