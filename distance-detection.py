import sys
import cv2
import numpy as np
from ultralytics import YOLO
import json
import os

car_id_map = {}

def extract_tracks(results):
    boxes, cls, trk_ids = [], [], []
    for result in results:
        boxes.extend(result.boxes.xyxy.cpu().numpy())
        cls.extend(result.boxes.cls.cpu().tolist())
        trk_ids.extend(result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(result.boxes.xyxy))
    return boxes, cls, trk_ids

def assign_ids_to_cars(current_cars, max_distance=50):
    global car_id_map
    next_id = max(car_id_map.keys(), default=-1) + 1
    new_car_map = {}
    for car in current_cars:
        car_center = [(car['x1'] + car['x2']) / 2, (car['y1'] + car['y2']) / 2]
        min_distance, assigned_id = float('inf'), None
        for prev_id, prev_car in car_id_map.items():
            prev_car_center = [(prev_car['x1'] + prev_car['x2']) / 2, (prev_car['y1'] + prev_car['y2']) / 2]
            distance = np.sqrt((car_center[0] - prev_car_center[0]) ** 2 + (car_center[1] - prev_car_center[1]) ** 2)
            if distance < min_distance and distance < max_distance:
                min_distance = distance
                assigned_id = prev_id
        if assigned_id is not None:
            car['id'] = assigned_id
            new_car_map[assigned_id] = car
        else:
            car['id'] = next_id
            new_car_map[next_id] = car
            next_id += 1
    car_id_map = new_car_map
    return current_cars

def detect_cars(image, model):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model(rgb_image)
    boxes, cls, trk_ids = extract_tracks(results)
    cars = [{'x1': box[0], 'y1': box[1], 'x2': box[2], 'y2': box[3], 'id': trk_id} 
            for box, cls_id, trk_id in zip(boxes, cls, trk_ids) if int(cls_id) in [2, 5, 7]]  # ID 2,5,7 pour 'car,bus,truck'
    return cars

def calculate_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

def convert_pixels_to_meters(pixels, reference_pixels, reference_meters):
    return (pixels / reference_pixels) * reference_meters if reference_pixels != 0 else float('inf')

def is_same_lane(car, source_point, lane_width):
    car_center_x = (car['x1'] + car['x2']) / 2
    return abs(car_center_x - source_point[0]) <= lane_width / 2

def find_closest_car_in_lane(cars, source_point, lane_width):
    min_distance, closest_car = float('inf'), None
    for car in cars:
        if is_same_lane(car, source_point, lane_width):
            center = [(car['x1'] + car['x2']) / 2, (car['y1'] + car['y2']) / 2]
            distance = calculate_distance(source_point, center)
            if distance < min_distance and distance > 0:
                min_distance = distance
                closest_car = car
    return closest_car, min_distance

def annotate_image(image, cars, closest_car=None, distance_meters=0, source_point=None):
    for car in cars:
        x1, y1, x2, y2 = int(car['x1']), int(car['y1']), int(car['x2']), int(car['y2'])
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, f'Car {car["id"]}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    if closest_car and source_point:
        center_closest = [(int(closest_car['x1']) + int(closest_car['x2'])) // 2, 
                          (int(closest_car['y1']) + int(closest_car['y2'])) // 2]
        cv2.line(image, source_point, tuple(center_closest), (0, 0, 255), 2)
        mid_point = ((source_point[0] + center_closest[0]) // 2, (source_point[1] + center_closest[1]) // 2)
        cv2.putText(image, f'Distance: {distance_meters:.2f} m', mid_point, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    return image
def main(video_path, json_path):
    # Only create directories if the json_path includes a directory
    if os.path.dirname(json_path):
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    model = YOLO("yolov8n.pt")

    average_car_width_meters = 1.8

    def get_source_point(image):
        h, w, _ = image.shape
        return (w // 2, h)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Erreur lors de la lecture du fichier vidéo: {video_path}")
        sys.exit(1)

    # Set the output path to be in the same directory as the script
    output_file = os.path.join(os.path.dirname(__file__), "output.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_file, fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))

    if not out.isOpened():
        print(f"Erreur lors de la création du fichier vidéo de sortie: {output_file}")
        sys.exit(1)

    lane_width = int(cap.get(3)) // 3

    distances = {}
    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        source_point = get_source_point(frame)
        cars = detect_cars(frame, model)
        if cars:
            cars = assign_ids_to_cars(cars)
            closest_car, distance_pixels = find_closest_car_in_lane(cars, source_point, lane_width)
            if closest_car:
                car_width_pixels = (closest_car['x2'] - closest_car['x1'])
                distance_meters = convert_pixels_to_meters(distance_pixels, car_width_pixels, average_car_width_meters)
                timestamp = frame_count / fps
                print(f"Time: {timestamp:.2f} seconds, Distance to the closest car (ID: {closest_car['id']}): {distance_meters:.2f} meters")
                annotated_frame = annotate_image(frame, cars, closest_car, distance_meters, source_point)

                car_id = closest_car['id']
                if car_id not in distances:
                    distances[car_id] = []
                distances[car_id].append({"timestamp": f"{timestamp:.2f} seconds", "distance": f"{distance_meters:.2f} meters"})
            else:
                annotated_frame = annotate_image(frame, cars, source_point=source_point)
        else:
            annotated_frame = frame

        out.write(annotated_frame)
        frame_count += 1

    cap.release()
    out.release()

    with open(json_path, 'w') as json_file:
        json.dump(distances, json_file, indent=4)

    print(f'Distances with timestamps have been saved to {json_path}')
    print(f'Output video has been saved to {output_file}')
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python distance-detection.py <video_path> <json_path>")
        sys.exit(1)

    main(sys.argv[1],sys.argv[2])
