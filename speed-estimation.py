import cv2
import json
from ultralytics import YOLO
from speed_estimator import SpeedEstimator
import sys
import os

def main(video_path, json_path, output_video_path):
    print(f"Processing video: {video_path}")
    print(f"Output JSON path: {json_path}")
    print(f"Output video path: {output_video_path}")

    # Load YOLO model and initialize
    model = YOLO("yolov8n.pt")
    names = model.model.names

    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error reading video file: {video_path}")
        return

    # Get video properties
    width, height, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))
    resize_factor = 1
    width = int(width * resize_factor)
    height = int(height * resize_factor)

    # Initialize SpeedEstimator
    speed_estimator = SpeedEstimator(names, reg_pts=[(0, int(height * 0.6)), (width, int(height * 0.6))])
    speed_estimator.set_video_writer(output_video_path, fps, width, height)

    # Initialize a dictionary to store unique speeds for each vehicle with timestamps
    distances = {}
    frame_count = 0

    # Process each frame
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("End of video or error reading frame.")
            break

        frame = cv2.resize(frame, (width, height))
        results = model.track(source=frame, persist=True)  # Using model.track to get tracking data

        # Calculate the timestamp in seconds
        timestamp = frame_count / fps

        # Estimate speed and annotate frame
        estimated_frame = speed_estimator.estimate_speed(frame, results)
        
        # Collect speeds with timestamps for each tracked vehicle, limiting to 8 values per vehicle
        for trk_id, speed_list in speed_estimator.dist_data.items():
            if trk_id not in distances:
                distances[trk_id] = []  # Initialize a list to store speed entries with timestamps

            if len(distances[trk_id]) < 8:  # Ensure only up to 8 speed entries are stored
                if isinstance(speed_list, list):  # Ensure speed_list is a list before processing
                    for speed in speed_list:
                        speed_rounded = round(speed, 2)  # Round to 2 decimal places
                        speed_entry = {"timestamp": f"{timestamp:.2f} s", "speed": f"{speed_rounded} km/h"}
                        distances[trk_id].append(speed_entry)
                        if len(distances[trk_id]) >= 8:
                            break  # Stop adding more speeds once we have 8 entries
                else:
                    speed_rounded = round(speed_list, 2)  # Handle unexpected type
                    speed_entry = {"timestamp": f"{timestamp:.2f} s", "speed": f"{speed_rounded} km/h"}
                    distances[trk_id].append(speed_entry)

        frame_count += 1

    # Release resources
    cap.release()
    speed_estimator.release_video_writer()

    # Save the results to a JSON file
    with open(json_path, 'w') as json_file:
        json.dump(distances, json_file, indent=4)

    # Print the URLs of the input video, JSON file, and output video
    print(f"Input Video URL: file:///{os.path.abspath(video_path).replace('\\', '/')}")
    print(f"JSON Output URL: file:///{os.path.abspath(json_path).replace('\\', '/')}")
    print(f"Output Video URL: file:///{os.path.abspath(output_video_path).replace('\\', '/')}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python distance-detection.py <video_path> <json_path> <output_video_path>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
