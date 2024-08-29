import cv2
import numpy as np
from collections import defaultdict
from ultralytics.utils.plotting import Annotator, colors

class SpeedEstimator:
    def __init__(self, names, reg_pts=None, view_img=False, line_thickness=2, region_thickness=5, spdl_dist_thresh=10):
        self.names = names
        self.reg_pts = reg_pts if reg_pts is not None else [(20, 400), (1260, 400)]
        self.line_thickness = line_thickness
        self.region_thickness = region_thickness
        self.spdl_dist_thresh = spdl_dist_thresh
        self.trk_history = defaultdict(list)
        self.dist_data = {}
        self.trk_previous_points = {}
        self.trk_idslist = []
        self.video_writer = None
        self.frame_width = None
        self.frame_height = None
        self.old_gray = None
        self.frame_rate = 30  # Define frame_rate as per your video
        self.scale_factor = 0.1  # Adjust scale factor as necessary

    def set_video_writer(self, output_path, frame_rate, width, height):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(output_path, fourcc, frame_rate, (width, height))
        self.frame_width = width
        self.frame_height = height
        self.frame_rate = frame_rate

    def write_frame(self, frame):
        if self.video_writer:
            self.video_writer.write(frame)

    def release_video_writer(self):
        if self.video_writer:
            self.video_writer.release()

    def extract_tracks(self, tracks):
        self.boxes = tracks[0].boxes.xyxy.cpu().numpy()
        self.clss = tracks[0].boxes.cls.cpu().tolist()
        self.trk_ids = tracks[0].boxes.id.int().cpu().tolist()

    def store_track_info(self, track_id, box):
        track = self.trk_history[track_id]
        bbox_center = (float((box[0] + box[2]) / 2), float((box[1] + box[3]) / 2))
        track.append(bbox_center)

        if len(track) > 30:
            track.pop(0)

        self.trk_pts = np.hstack(track).astype(np.int32).reshape((-1, 1, 2))
        return track

    def calculate_speed(self, trk_id, track, flow):
        centroid_x = int(track[-1][0])
        centroid_y = int(track[-1][1])

        if flow is not None:
            if self.reg_pts[0][0] < centroid_x < self.reg_pts[1][0] and \
               self.reg_pts[1][1] - self.spdl_dist_thresh < centroid_y < self.reg_pts[1][1] + self.spdl_dist_thresh:
                flow_at_centroid = flow[centroid_y, centroid_x]
                flow_x, flow_y = flow_at_centroid
                speed_pixels_per_frame = np.linalg.norm((flow_x, flow_y))
                speed_kmh = speed_pixels_per_frame * self.frame_rate * self.scale_factor * 3.6
                self.dist_data[trk_id] = speed_kmh

    def estimate_speed(self, im0, tracks, region_color=(255, 0, 0)):
        self.im0 = im0
        gray = cv2.cvtColor(im0, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(self.old_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0) if self.old_gray is not None else None
        
        if tracks[0].boxes.id is None:
            return im0

        self.extract_tracks(tracks)
        self.annotator = Annotator(self.im0, line_width=self.line_thickness)
        self.annotator.draw_region(reg_pts=self.reg_pts, color=region_color, thickness=self.region_thickness)

        for box, trk_id, cls in zip(self.boxes, self.trk_ids, self.clss):
            track = self.store_track_info(trk_id, box)

            if trk_id not in self.trk_previous_points:
                self.trk_previous_points[trk_id] = track[-1]

            self.calculate_speed(trk_id, track, flow)
            self.plot_box_and_track(trk_id, box, cls)

        self.write_frame(im0)  # Write the frame to the video output
        self.old_gray = gray

        return im0

    def plot_box_and_track(self, track_id, box, cls):
        speed_label = f"{self.dist_data.get(track_id, 0):.2f} km/h" if track_id in self.dist_data else self.names[int(cls)]
        bbox_color = colors(int(track_id)) if track_id in self.dist_data else (255, 0, 255)

        self.annotator.box_label(box, speed_label, bbox_color)
        cv2.circle(self.im0, (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)), 5, bbox_color, -1)
