from ..common_util.standard import StandardPlugin
from . import Repositories
import cv2
import math
import uuid
from ..common_util import global_catch
import numpy as np


class TrackingArea:
    def __init__(self, start_line, end_line):
        self.start_line = start_line
        self.end_line = end_line

    @staticmethod
    def cross_line(line, point_a, point_b):
        is_cross = False
        [(x1, y1), (x2, y2)] = line
        (xA, yA) = point_a
        v1_x = x2 - x1
        v1_y = y2 - y1
        v2_x = x2 - xA
        v2_y = y2 - yA
        xp = v1_x * v2_y - v1_y * v2_x
        if xp < 0:
            is_cross = True
        return is_cross

    def cross_start_line(self, last_point, current_point):
        return self.cross_line(self.start_line, last_point, current_point)

    def cross_end_line(self, last_point, current_point):
        return self.cross_line(self.end_line, last_point, current_point)


class TrackingItem:
    def __init__(self, tracker, detect_item, tracker_id, label):
        Repositories.sequence_id += 1
        self.sequence_id = Repositories.sequence_id
        self.label = label
        self.tracker = tracker
        self.detect_item = detect_item
        self.tracker_id = tracker_id
        self.can_track = True
        self.last_center = (-1, -1)
        self.line_start_counted = False
        self.line_end_counted = False

    def get_center(self):
        (tmp_label, tmp_confidence, tmp_xmin, tmp_ymin, tmp_xmax, tmp_ymax) = self.detect_item
        tmp_center_x = (tmp_xmin + tmp_xmax) / 2
        tmp_center_y = (tmp_ymin + tmp_ymax) / 2
        return tmp_center_x, tmp_center_y

    def update(self, _frame, label):
        self.label = label
        # if self.get_center() > self.last_center:
        self.last_center = self.get_center()
        ok, _bbox = self.tracker.update(_frame)
        (xmin, ymin, width, height) = _bbox
        self.detect_item = (
            self.label, 1, xmin, ymin, xmin + width, ymin + height)
        return ok, self.detect_item

    def update_tracker(self, tracker):
        self.tracker = tracker

    def update_detect_item(self, detect_item):
        self.detect_item = detect_item

    def update_can_track(self, can_track):
        self.can_track = can_track

    def start_counted(self):
        self.line_start_counted = True

    def end_counted(self):
        self.line_end_counted = True


car_type_list = {
    "green taxi": [1, 0, 0],
    "red taxi": [2, 0, 0],
    "van": [3, 0, 0],
    "bus": [4, 0, 0],
    "truck": [5, 0, 0],
    "blue taxi": [6, 0, 0],
    "private car": [7, 0, 0],
    "motorcycle": [8, 0, 0],
    "mini bus": [9, 0, 0],
    "flatbed truck": [10, 0, 0],
    "concrete mixer truck": [11, 0, 0],
    "other": [12, 0, 0]}


def increase_car_type_count(car_type, field):
    matrix = car_type_list[car_type]
    print(car_type)
    matrix[field] += 1
    print(matrix)


def display_car_counting(_frame, total_count):
    car_type_set = car_type_list.keys()
    for car_type in car_type_set:
        if car_type and len(car_type_list[car_type]) == 3:

            sid = car_type_list[car_type][0]
            number = int(
                (car_type_list[car_type][1] + car_type_list[car_type][2]) / 2)

            posi_x = (sid - 1) % 2 * 300 + 1020
            posi_y = 73 * ((sid - 1) // 2) + 20
            cv2.putText(_frame, str(number), (posi_x, posi_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            percentage = "(0%)"
            if total_count > 0:
                percentage_number = int(number * 100 / total_count)
                percentage = "(" + str(percentage_number) + "%)"

            cv2.putText(_frame, percentage, (posi_x + 30, posi_y + 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)


def is_existing_item(detect_item):
    (label, confidence, xmin, ymin, xmax, ymax) = detect_item
    cx = int((xmin + xmax) / 2)
    cy = int((ymin + ymax) / 2)
    box_range = ((xmax - xmin) + (ymax - ymin)) / 2
    for tracking_item in Repositories.all_item_list:
        (label, confidence, xmin, ymin, xmax, ymax) = tracking_item.detect_item
        tx = int((xmin + xmax) / 2)
        ty = int((ymin + ymax) / 2)
        if math.sqrt((cx - tx) * (cx - tx) + (cy - ty) * (cy - ty)) < box_range:
            return True, tracking_item
    return False, None


def in_exit_zone():
    return False


def create_tracker(tracker_type):
    tracker = None
    if tracker_type == 'BOOSTING':
        tracker = cv2.TrackerBoosting_create()
    if tracker_type == 'MIL':
        tracker = cv2.TrackerMIL_create()
    if tracker_type == 'KCF':
        tracker = cv2.TrackerKCF_create()
    if tracker_type == 'TLD':
        tracker = cv2.TrackerTLD_create()
    if tracker_type == 'MEDIANFLOW':
        tracker = cv2.TrackerMedianFlow_create()
    if tracker_type == 'GOTURN':
        tracker = cv2.TrackerGOTURN_create()
    return tracker


class CarCountingPlugin(StandardPlugin):
    def __init__(self):
        super().__init__()
        self.interval = 2
        self.tracking_area = TrackingArea(Repositories.start_line,
                                          Repositories.end_line)

    def process_new_frame(self):

        frame_id = self.current_frame
        current_idx = frame_id % 1000
        if frame_id % self.interval == 0:
            self._detect()
            detected_item_list = global_catch.frame_catch[current_idx]

            for detected_item in detected_item_list:

                (label, confidence, xmin, ymin, xmax, ymax) = detected_item
                tracker_box = (xmin, ymin, xmax - xmin, ymax - ymin)
                is_exist, _tmp_item = is_existing_item(detected_item)
                tracker = create_tracker("KCF")
                tracker.init(self.frame, tracker_box)

                if is_exist:
                    _tmp_item.update_tracker(tracker)
                    # print(tracker_box)
                    can_track, __bbox = _tmp_item.update(self.frame, label)
                    # print(__bbox)
                    _tmp_item.update_can_track(can_track)
                else:
                    tracker_id = str(uuid.uuid4())
                    _tmp_item = TrackingItem(tracker=tracker,
                                             detect_item=detected_item,
                                             tracker_id=tracker_id,
                                             label=label)
                    can_track, _ = _tmp_item.update(self.frame, label)
                    Repositories.all_item_list.append(_tmp_item)

        else:
            for _tmp_item in Repositories.all_item_list:
                can_track, _ = _tmp_item.update(self.frame, _tmp_item.label)
                _tmp_item.update_can_track(can_track)

        tmp_all_item = []
        for _tmp_item in Repositories.all_item_list:
            if _tmp_item.can_track:
                tmp_all_item.append(_tmp_item)
        Repositories.all_item_list = tmp_all_item

        for _tmp_item in Repositories.all_item_list:
            current_center_point = _tmp_item.get_center()
            last_center_point = _tmp_item.last_center
            (last_x, last_y) = last_center_point
            if last_x == -1 or last_y == -1:
                _tmp_item.last_center = current_center_point
            if (not _tmp_item.line_start_counted) and self.tracking_area.cross_start_line(
                    last_center_point, current_center_point):
                Repositories.over_start_counter += 1
                increase_car_type_count(_tmp_item.label, 1)
                _tmp_item.start_counted()

            elif (not _tmp_item.line_end_counted) and self.tracking_area.cross_end_line(
                    last_center_point, current_center_point):
                Repositories.over_end_counter += 1
                increase_car_type_count(_tmp_item.label, 2)
                _tmp_item.end_counted()

    def handle(self):
        self.process_new_frame()
        for item in Repositories.all_item_list:
            (label, confidence, xmin, ymin, xmax, ymax) = item.detect_item
            center_x = int((xmin + xmax) / 2)
            center_y = int((ymin + ymax) / 2)
            center = (center_x, center_y)
            cv2.circle(img=self.frame, center=center, radius=7, color=(0, 0, 255), thickness=4)
            cv2.putText(self.frame, "  " + item.label, center, cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 0, 255), 2)

        car_count = max(Repositories.over_start_counter, Repositories.over_end_counter)
        car_count = int(car_count)

        tmp_diff = abs(Repositories.over_start_counter - Repositories.over_end_counter)
        if tmp_diff >= 2:
            if Repositories.over_start_counter < Repositories.over_end_counter:
                Repositories.over_start_counter += 1
            if Repositories.over_start_counter > Repositories.over_end_counter:
                Repositories.over_end_counter += 1

        [_start_point_1, _start_point_2] = Repositories.start_line
        [_end_point_1, _end_point_2] = Repositories.end_line

        overlay = self.frame.copy()
        output = self.frame.copy()
        pts = np.array([_start_point_1, _start_point_2, _end_point_2, _end_point_1, _start_point_1])

        cv2.fillConvexPoly(overlay, pts, (255, 0, 0))
        alpha = 0.5
        cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)

        # Display result
        car_sum = 0
        car_type_set = car_type_list.keys()
        for car_type in car_type_set:
            if car_type and len(car_type_list[car_type]) == 3:
                car_sum += int((car_type_list[car_type][1] +
                                car_type_list[car_type][2]) / 2)
        # car_sum = int(car_sum/2)
        if car_count > car_sum:
            car_count = car_sum
        display_car_counting(output, car_count)
        cv2.putText(output, str(car_count), (1300, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (55, 175, 212), 2)
        self.frame = output
