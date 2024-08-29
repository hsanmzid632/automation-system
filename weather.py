import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import cv2
import numpy as np
import json
import os

# Choisir MobileNet ou DenseNet121
# model = models.mobilenet_v2(pretrained=True)  # Pour MobileNet
model = models.densenet121(pretrained=True)  # Pour DenseNet121

# Adapter la dernière couche pour 5 classes météorologiques
if isinstance(model, models.DenseNet):
    model.classifier = nn.Linear(model.classifier.in_features, 5)
elif isinstance(model, models.ResNet):
    model.fc = nn.Linear(model.fc.in_features, 5)

model.eval()

# Define preprocessing transformation
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Weather class labels
class_labels = ['sunny', 'cloudy', 'foggy', 'snowy', 'rainy']

# Load a model trained for rain intensity detection
rain_intensity_model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet18', weights='ResNet18_Weights.DEFAULT')
rain_intensity_model.fc = nn.Linear(rain_intensity_model.fc.in_features, 1)  # Regression output for rain intensity
rain_intensity_model.eval()

def preprocess_image(image):
    return preprocess(image).unsqueeze(0)

def predict_weather(image):
    with torch.no_grad():
        input_tensor = preprocess_image(image)
        output = model(input_tensor)
        
        # Affichage des valeurs de sortie du modèle
        print(f"Model output (raw): {output.numpy()}")  # Debugging statement
        
        # Identification de la classe prédite
        _, predicted = torch.max(output, 1)
        predicted_index = predicted.item()
        
        print(f"Predicted index: {predicted_index}")  # Debugging statement
        
        # Vérification de l'index prédit
        if predicted_index < len(class_labels):
            predicted_label = class_labels[predicted_index]
            print(f"Predicted label: {predicted_label}")  # Debugging statement
            return predicted_label
        else:
            print(f"Warning: Predicted index {predicted_index} is out of bounds for class_labels")
            return "unknown"

def predict_rain_intensity(image):
    with torch.no_grad():
        input_tensor = preprocess_image(image)
        output = rain_intensity_model(input_tensor)
        rain_percentage = torch.sigmoid(output).item() * 100  # Convert to percentage
        return rain_percentage

def main(video_path, json_path):
    # Check if the directory is specified
    directory = os.path.dirname(json_path)
    if directory:  # Only create directory if it is specified
        os.makedirs(directory, exist_ok=True)

    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Set the output path to be in the same directory as the script
    output_video_path = os.path.join(os.path.dirname(__file__), "processed_weather_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print(f"Error creating output video file: {output_video_path}")
        return

    # List to store results
    results = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        predicted_class = predict_weather(image)

        if predicted_class == 'rainy':
            rain_percentage = predict_rain_intensity(image)
            rain_info = f"{rain_percentage:.2f}%"
        else:
            rain_info = 'N/A'

        gray_image = image.convert('L')
        avg_brightness = np.mean(np.array(gray_image))
        day_or_night = 'day' if avg_brightness > 100 else 'night'

        frame_with_text = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        cv2.putText(frame_with_text, f"Weather: {predicted_class}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame_with_text, f"Rain: {rain_info}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame_with_text, f"Time: {day_or_night}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        out.write(frame_with_text)

        # Append results for each frame
        results.append({
            "weather": predicted_class,
            "rain_intensity": rain_info,
            "time_of_day": day_or_night
        })

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # Save results to JSON file
    with open(json_path, 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print(f"Processed video saved as {output_video_path}")
    print(f"Weather results saved as {json_path}")

if __name__ == "__main__":
    main("trafic1.mp4", "weather.json")
