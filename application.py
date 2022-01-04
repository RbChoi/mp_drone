#!/usr/bin/env python
# -*- coding: utf-8 -*-
import configargparse
from flask import Flask, url_for, request, render_template, Response
from flask_cors import CORS

import cv2 as cv

from gestures.tello_gesture_controller import TelloGestureController
from utils import CvFpsCalc

from djitellopy import Tello
from gestures import *

import threading

application = Flask(__name__)
CORS(application)


def get_args():
    # print('## Reading configuration ##')
    parser = configargparse.ArgParser(default_config_files=['config.txt'])

    parser.add('-c', '--my-config', required=False, is_config_file=True, help='config file path')
    parser.add("--device", type=int)
    parser.add("--width", help='cap width', type=int)
    parser.add("--height", help='cap height', type=int)
    parser.add("--is_keyboard", help='To use Keyboard control by default', type=bool)
    parser.add('--use_static_image_mode', action='store_true', help='True if running on photos')
    parser.add("--min_detection_confidence",
               help='min_detection_confidence',
               type=float)
    parser.add("--min_tracking_confidence",
               help='min_tracking_confidence',
               type=float)
    parser.add("--buffer_len",
               help='Length of gesture buffer',
               type=int)

    args = parser.parse_args()

    return args


def select_mode(key, mode):
    number = -1
    if 48 <= key <= 57:  # 0 ~ 9
        number = key - 48
    if key == 110:  # n
        mode = 0
    if key == 107:  # k
        mode = 1
    if key == 104:  # h
        mode = 2
    return number, mode


@application.route('/main')
def main():
    # init global vars
    global gesture_buffer
    global gesture_id
    global battery_status

    # Argument parsing
    args = get_args()
    KEYBOARD_CONTROL = args.is_keyboard
    WRITE_CONTROL = False
    in_flight = False

    # Camera preparation
    # tello = Tello()
    # tello.connect()
    # tello.streamon()

    # cap = tello.get_frame_read()
    cap = cv.VideoCapture(1)

    # Init Tello Controllers
    # gesture_controller = TelloGestureController(tello)
    # keyboard_controller = TelloKeyboardController(tello)

    gesture_detector = GestureRecognition(args.use_static_image_mode, args.min_detection_confidence,
                                          args.min_tracking_confidence)
    gesture_buffer = GestureBuffer(buffer_len=args.buffer_len)

    '''
    def tello_control(key, keyboard_controller, gesture_controller):
        global gesture_buffer

        if KEYBOARD_CONTROL:
            keyboard_controller.control(key)
        else:
            gesture_controller.gesture_control(gesture_buffer)

    def tello_battery(tello):
        global battery_status
        try:
            battery_status = tello.get_battery()[:-2]
        except:
            battery_status = -1
'''

    # FPS Measurement
    cv_fps_calc = CvFpsCalc(buffer_len=10)

    mode = 0
    number = -1
    battery_status = -1

    # tello.move_down(20)

    while True:
        fps = cv_fps_calc.get()

        # Process Key (ESC: end)
        key = cv.waitKey(1) & 0xff
        if key == 27:  # ESC
            break
        elif key == 32:  # Space
            if not in_flight:
                # Take-off drone
                # tello.takeoff()
                in_flight = True

            elif in_flight:
                # Land tello
                # tello.land()
                in_flight = False

        elif key == ord('k'):
            mode = 0
            KEYBOARD_CONTROL = True
            WRITE_CONTROL = False
            # tello.send_rc_control(0, 0, 0, 0)  # Stop moving
        elif key == ord('g'):
            KEYBOARD_CONTROL = False
        elif key == ord('n'):
            mode = 1
            WRITE_CONTROL = True
            KEYBOARD_CONTROL = True

        if WRITE_CONTROL:
            number = -1
            if 48 <= key <= 57:  # 0 ~ 9
                number = key - 48

        # Camera capture
        success, image = cap.read()

        debug_image, gesture_id = gesture_detector.recognize(image, number, mode)
        gesture_buffer.add_gesture(gesture_id)

        # Start control thread
        # threading.Thread(target=tello_control, args=(key, keyboard_controller, gesture_controller,)).start()
        # threading.Thread(target=tello_battery, args=(tello,)).start()

        debug_image = gesture_detector.draw_info(debug_image, fps, mode, number)

        if not success:
            break
        else:
            # Battery status and image rendering
            cv.putText(debug_image, "Battery: {}".format(battery_status), (5, 720 - 5),
                       cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            ret, buffer = cv.imencode('.jpg', debug_image)
            debug_image = buffer.tobytes()

        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + debug_image + b'\r\n')

        # cv.imshow('Tello Gesture Recognition', debug_image)

    # tello.land()
    # tello.end()
    cv.destroyAllWindows()
    return 'OK'


@application.route('/video')
def video():
    # return Response(createThread(),mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(main(), mimetype='multipart/x-mixed-replace; boundary=frame')


@application.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    # orginal
    application.run(host='0.0.0.0', debug=True)
