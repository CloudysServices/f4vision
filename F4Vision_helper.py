import cv2
import gtuner
import numpy as np
import os
import json
import importlib
import time
from collections import deque

class F4Vision:
    def __init__(self):
        self.currentFrame = 0
        self.last_settings_check = 0
        self.settings_check_interval = 0.05
        self.cached_settings = None
        self.settings_file = "settings.py"
        self.last_file_mtime = 0
        
        # Cache for settings values
        self.cached_bbox_width = 720
        self.cached_bbox_height = 480
        self.cached_color = [102, 51, 153]
        self.cached_showBoundingBox = True
        self.cached_adaptiveBoundingBox = False
        self.cached_manualOveride = True
        self.cached_speedX = 9
        self.cached_speedY = 9
        self.cached_aimSmoothing = False
        self.cached_colorConfidence = 0.21
        
        # NEW: ESP settings 
        self.cached_esp_lines_enabled = True
        self.cached_esp_box_enabled = True
        self.cached_crosshair_enabled = True
        self.cached_show_distance_text = True
        self.cached_enemy_location_enabled = True
        
        # Color ranges from debug log (optimized values)
        self.cached_pxd_low_color = np.array([61, 0, 102])   # From successful log
        self.cached_pxd_high_color = np.array([255, 45, 254]) # From successful log
        
        # Enemy size filtering from debug log (optimized values)
        self.cached_enemy_size_range = {
            'min_width': 5, 'max_width': 12,
            'min_height': 5, 'max_height': 12
        }
        
        # Aim offset cache
        self.cached_aimOffsetX = 0
        self.cached_aimOffsetY = 0
        
        # Manual override percentage cache
        self.cached_manualOverridePercentage = 50
        
        # Detection parameters
        self.detection_history = deque(maxlen=5)
        self.target_stability_threshold = 2
        
        # PXD file detection settings
        self.pxd_patterns = []
        self.active_pxd_file = None
        self.pxd_control_file = "pxd_control.json"
        self.last_pxd_check = 0
        self.pxd_check_interval = 0.5
        
        # NEW: Debug logging
        self.debug_mode = True
        self.log_file = "f4vision_debug.log"
        
        self.log("F4Vision initialized - Enhanced with optimized detection")

    def get_aim_button_id(self):
        """Get the aim button ID directly from settings using button constants"""
        try:
            # Force reload of settings file every time
            import settings
            import importlib
            importlib.reload(settings)
        
            # Get the button constant directly from settings
            button_constant = getattr(settings, "aimActivationButton", "BUTTON_7")
        
            # Direct mapping - no translation needed for friendly names
            button_mapping = {
                "BUTTON_5": 5,  # L1
                "BUTTON_6": 6,  # L2  
                "BUTTON_7": 7,  # R1
                "BUTTON_8": 8,  # R2
                "L1": 5,  # Backward compatibility
                "L2": 6,  # Backward compatibility
                "R1": 7,  # Backward compatibility  
                "R2": 8   # Backward compatibility
            }
        
            button_id = button_mapping.get(button_constant, 7)  # Default to BUTTON_7/R1
        
            # DEBUG: Log what we're reading and sending
            self.log(f"AIM BUTTON DEBUG: Read '{button_constant}' from settings -> Sending ID {button_id} to GPC")
        
            return button_id

        except Exception as e:
            self.log(f"ERROR reading aimActivationButton: {e}")
            return 7  # Default to BUTTON_7/R1

    def log(self, message):
        """Enhanced logging similar to debug log"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - DEBUG - {message}"
        print(log_message)
        
        # Optional: Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_message + '\n')
        except:
            pass

    def check_pxd_control(self):
        """Enhanced PXD control with logging"""
        current_time = time.time()
        
        if current_time - self.last_pxd_check > self.pxd_check_interval:
            self.last_pxd_check = current_time
            
            try:
                if os.path.exists(self.pxd_control_file):
                    with open(self.pxd_control_file, 'r') as f:
                        control_data = json.load(f)
                    
                    new_pxd_file = control_data.get('active_pxd_file')
                    pxd_directory = control_data.get('pxd_directory', r"C:\GtunerIV\scripts\F4VisionCV-main\F4VisionCV-main\pxd")
                    
                    if new_pxd_file != self.active_pxd_file:
                        if new_pxd_file:
                            self.load_single_pxd_file(os.path.join(pxd_directory, new_pxd_file))
                            self.active_pxd_file = new_pxd_file
                            self.log(f"PXD file loaded: {self.active_pxd_file}")
                        else:
                            self.unload_pxd_files()
                            self.active_pxd_file = None
                            self.log("PXD files unloaded")
                
                else:
                    if self.active_pxd_file is not None:
                        self.unload_pxd_files()
                        self.active_pxd_file = None
                        self.log("PXD files unloaded (no control file)")
                        
            except Exception as e:
                self.log(f"Error checking PXD control: {e}")

    def load_single_pxd_file(self, filepath):
        """Load PXD file with enhanced logging and optimized settings"""
        self.pxd_patterns = []
        
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
            
            pattern_data = json.loads(content)
            
            # USE OPTIMIZED COLOR RANGES FROM DEBUG LOG instead of PXD file colors
            pattern_data['color_lower_bgr'] = self.cached_pxd_low_color
            pattern_data['color_upper_bgr'] = self.cached_pxd_high_color
            
            # USE OPTIMIZED SIZE RANGE FROM DEBUG LOG
            pattern_data['size'] = {
                'width': [self.cached_enemy_size_range['min_width'], self.cached_enemy_size_range['max_width']],
                'height': [self.cached_enemy_size_range['min_height'], self.cached_enemy_size_range['max_height']]
            }
            
            pattern_data['source_file'] = os.path.basename(filepath)
            self.pxd_patterns.append(pattern_data)
            
        except Exception as e:
            self.log(f"Error loading PXD file {filepath}: {e}")

    def unload_pxd_files(self):
        """Unload PXD patterns with logging"""
        self.pxd_patterns = []
        self.log("All PXD patterns unloaded")

    def get_fresh_settings(self):
        """Enhanced settings loading with optimized defaults"""
        current_time = time.time()
        
        if current_time - self.last_settings_check > self.settings_check_interval:
            self.last_settings_check = current_time
            
            try:
                current_mtime = os.path.getmtime(self.settings_file)
                if current_mtime > self.last_file_mtime:
                    self.last_file_mtime = current_mtime
                    import settings
                    importlib.reload(settings)
                    self.cached_settings = settings
                    
                    # Update cached values
                    self.cached_bbox_width = getattr(settings, 'boundingBoxWidth', 720)
                    self.cached_bbox_height = getattr(settings, 'boundingBoxHeight', 480)
                    self.cached_color = [settings.boundingBoxColor[0], settings.boundingBoxColor[1], settings.boundingBoxColor[2]]
                    self.cached_showBoundingBox = settings.showBoundingBox
                    self.cached_adaptiveBoundingBox = settings.adaptiveBoundingBox
                    self.cached_manualOveride = settings.manualOveride
                    self.cached_speedX = settings.speedX
                    self.cached_speedY = settings.speedY
                    self.cached_aimSmoothing = settings.aimSmoothing
                    
                    self.cached_colorConfidence = getattr(settings, 'colorConfidence', 0.21)
                    self.cached_aimOffsetX = getattr(settings, 'aimOffsetX', 0)
                    self.cached_aimOffsetY = getattr(settings, 'aimOffsetY', 0)
                    self.cached_manualOverridePercentage = getattr(settings, 'manualOverridePercentage', 50)
                    
                    self.log("Settings reloaded from file")
                    
            except Exception as e:
                self.log(f"Error reloading settings: {e}")
    
        return self.cached_settings

    def detect_with_pxd_patterns(self, frame):
        """Enhanced detection with proper size filtering and clustering"""
        self.check_pxd_control()
        
        all_detections = []
        
        if self.pxd_patterns:
            for pattern in self.pxd_patterns:
                detections = self.detect_all_pixels(frame, pattern)
                all_detections.extend(detections)
        
        # Log detection results like in debug log
        if all_detections:
            self.log(f"Found {len(all_detections)} raw enemies")
            
            # Apply clustering like in debug log
            clustered_detections = self.cluster_similar_enemies(all_detections)
            self.log(f"Reduced {len(all_detections)} enemies to {len(clustered_detections)} clusters")
            
            return clustered_detections
        
        return all_detections

    def cluster_similar_enemies(self, detections):
        """Cluster nearby detections like in debug log"""
        if not detections:
            return []
        
        # Simple clustering: group detections that are very close
        clusters = []
        used_indices = set()
        
        for i, det in enumerate(detections):
            if i in used_indices:
                continue
                
            cluster = [det]
            used_indices.add(i)
            x1, y1, x2, y2 = det['coords']
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            
            for j, other_det in enumerate(detections):
                if j in used_indices:
                    continue
                    
                ox1, oy1, ox2, oy2 = other_det['coords']
                other_center_x, other_center_y = (ox1 + ox2) // 2, (oy1 + oy2) // 2
                
                # If centers are within 10 pixels, cluster them
                distance = ((center_x - other_center_x) ** 2 + (center_y - other_center_y) ** 2) ** 0.5
                if distance < 10:
                    cluster.append(other_det)
                    used_indices.add(j)
            
            # Use the largest detection in the cluster
            if cluster:
                best_in_cluster = max(cluster, key=lambda x: x['area'])
                clusters.append(best_in_cluster)
        
        return clusters

    def detect_all_pixels(self, frame, pattern):
        """Enhanced detection with proper logging and optimized filtering"""
        detected_boxes = []
        
        try:
            lower_color = pattern['color_lower_bgr']
            upper_color = pattern['color_upper_bgr']
            
            mask = cv2.inRange(frame, lower_color, upper_color)
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
            
            min_width = pattern['size']['width'][0]
            max_width = pattern['size']['width'][1]
            min_height = pattern['size']['height'][0]
            max_height = pattern['size']['height'][1]
            
            for i in range(1, num_labels):
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                area = stats[i, cv2.CC_STAT_AREA]
                
                # Log filtering like in debug log
                if not (min_width <= w <= max_width) or not (min_height <= h <= max_height):
                    self.log(f"Filtered enemy: size {w}x{h} outside range {min_width}-{max_width} x {min_height}-{max_height}")
                    continue
                
                detected_boxes.append({
                    'coords': (x, y, x + w, y + h),
                    'confidence': 0.9,
                    'width': w,
                    'height': h,
                    'area': area,
                    'center': (x + w//2, y + h//2),
                    'pixel_count': area
                })
            
        except Exception as e:
            self.log(f"Error in pixel detection: {e}")
        
        return detected_boxes

    def draw_esp_elements(self, frame, detections, roi_offset_x=0, roi_offset_y=0):
        """Draw ESP lines, boxes, and crosshair"""
        if not self.cached_enemy_location_enabled:
            return frame
            
        screen_center = (960, 540)
        
        for detection in detections:
            x1, y1, x2, y2 = detection['coords']
            # Adjust coordinates for ROI offset
            x1 += roi_offset_x
            y1 += roi_offset_y
            x2 += roi_offset_x
            y2 += roi_offset_y
            
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Draw ESP lines
            if self.cached_esp_lines_enabled:
                line_color = (0, 255, 255)  # Cyan
                cv2.line(frame, screen_center, (center_x, center_y), line_color, 2)
            
            # Draw ESP boxes
            if self.cached_esp_box_enabled:
                box_color = (128, 128, 255)  # Light purple
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            
            # Draw distance text
            if self.cached_show_distance_text:
                distance = ((center_x - screen_center[0]) ** 2 + (center_y - screen_center[1]) ** 2) ** 0.5
                cv2.putText(frame, f"{int(distance)}px", (center_x, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw crosshair
        if self.cached_crosshair_enabled:
            crosshair_size = 30
            crosshair_color = (0, 255, 0)  # Green
            cv2.line(frame, (screen_center[0] - crosshair_size, screen_center[1]), 
                    (screen_center[0] + crosshair_size, screen_center[1]), crosshair_color, 2)
            cv2.line(frame, (screen_center[0], screen_center[1] - crosshair_size), 
                    (screen_center[0], screen_center[1] + crosshair_size), crosshair_color, 2)
        
        return frame

    def simple_detection_sort(self, detections):
        if not detections:
            return []
        sorted_detections = sorted(detections, key=lambda x: x['area'], reverse=True)
        confidence_threshold = self.cached_colorConfidence
        return [d for d in sorted_detections if d['confidence'] >= confidence_threshold]

    def apply_temporal_filtering(self, current_detections):
        if not current_detections:
            self.detection_history.append([])
            return []
        self.detection_history.append(current_detections)
        return current_detections

    @staticmethod
    def rectangleScaling(x1, y1, x2, y2):
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    def draw_white_highlight(self, img, pt1, pt2, thickness=2):
        x1, y1 = pt1
        x2, y2 = pt2
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), thickness)
        return img

    def apply_aim_offset(self, x1, y1, x2, y2, offset_x, offset_y):
        if offset_x == 0 and offset_y == 0:
            return x1, y1, x2, y2
        offset_pixels_x = offset_x * 1.0
        offset_pixels_y = offset_y * 1.0
        new_x1 = x1 + int(offset_pixels_x)
        new_y1 = y1 + int(offset_pixels_y)
        new_x2 = x2 + int(offset_pixels_x)
        new_y2 = y2 + int(offset_pixels_y)
        return new_x1, new_y1, new_x2, new_y2

    def perfect_target_lock(self, target_x, target_y, speedX, speedY):
        """PERFECT LOCK - Directly moves crosshair to target center"""
        crosshair_x, crosshair_y = 960, 540
        
        # Calculate exact pixel difference
        delta_x = target_x - crosshair_x
        delta_y = target_y - crosshair_y
        
        # Calculate distance for movement scaling
        distance = (delta_x ** 2 + delta_y ** 2) ** 0.5
        
        # PERFECT LOCK LOGIC: Direct movement to target
        if distance < 2:  # Already perfectly locked
            return 0, 0
        
        # Calculate movement vector directly to target
        # Use speed settings to control how fast we lock
        base_multiplier = 0.02  # Direct movement multiplier
        
        # Apply speed scaling
        move_x = delta_x * base_multiplier * speedX
        move_y = delta_y * base_multiplier * speedY
        
        # Ensure minimum movement for fine adjustments
        min_move = 0.5
        if abs(move_x) < min_move and abs(delta_x) > 0.5:
            move_x = min_move if delta_x > 0 else -min_move
        if abs(move_y) < min_move and abs(delta_y) > 0.5:
            move_y = min_move if delta_y > 0 else -min_move
        
        return (move_x, move_y)

    def predict(self, frame, button_5, button_7, button_9):
        """MAIN PREDICTION METHOD - Enhanced with ESP drawing"""
        self.get_fresh_settings()
        
        bbox_width = self.cached_bbox_width
        bbox_height = self.cached_bbox_height
        showBoundingBox = self.cached_showBoundingBox
        adaptiveBoundingBox = self.cached_adaptiveBoundingBox
        manualOveride = self.cached_manualOveride
        speedX = self.cached_speedX
        speedY = self.cached_speedY
        aimSmoothing = self.cached_aimSmoothing
        
        aimOffsetX = self.cached_aimOffsetX
        aimOffsetY = self.cached_aimOffsetY
        
        # Get manual override percentage
        manualOverridePercentage = self.cached_manualOverridePercentage
        
        rx, ry = 0, 0
        final = frame
        
        screen_center_x, screen_center_y = 960, 540
        X1 = max(0, screen_center_x - bbox_width // 2)
        Y1 = max(0, screen_center_y - bbox_height // 2)
        X2 = min(1920, screen_center_x + bbox_width // 2)
        Y2 = min(1080, screen_center_y + bbox_height // 2)
        
        if adaptiveBoundingBox and button_7 > 0:
            adaptive_multiplier = 1.5
            adaptive_width = int(bbox_width * adaptive_multiplier)
            adaptive_height = int(bbox_height * adaptive_multiplier)
            X1 = max(0, screen_center_x - adaptive_width // 2)
            Y1 = max(0, screen_center_y - adaptive_height // 2)
            X2 = min(1920, screen_center_x + adaptive_width // 2)
            Y2 = min(1080, screen_center_y + adaptive_height // 2)
        
        ROI = {"X1": X1, "Y1": Y1, "X2": X2, "Y2": Y2}
        
        if Y2 > Y1 and X2 > X1:
            img0 = frame[ROI["Y1"]:ROI["Y2"], ROI["X1"]:ROI["X2"], :]
        else:
            img0 = frame
        
        if showBoundingBox:
            cv2.rectangle(final, (X1, Y1), (X2, Y2), (255, 255, 255), 1)
        
        detected_objects = self.detect_with_pxd_patterns(img0)
        all_targets = self.apply_temporal_filtering(detected_objects)
        
        best_target = None
        if all_targets:
            best_target = max(all_targets, key=lambda x: x['area'])
            for target in all_targets:
                x1, y1, x2, y2 = target['coords']
                x1, y1, x2, y2 = (x1 + X1), (y1 + Y1), (x2 + X1), (y2 + Y1)
                final = self.draw_white_highlight(final, (x1, y1), (x2, y2), 1)
        
        # NEW: Draw ESP elements if enemy location is enabled
        if self.cached_enemy_location_enabled and all_targets:
            final = self.draw_esp_elements(final, all_targets, X1, Y1)
        
        if best_target:
            x1, y1, x2, y2 = best_target['coords']
            x1, y1, x2, y2 = (x1 + X1), (y1 + Y1), (x2 + X1), (y2 + Y1)
            
            # Calculate target center
            target_center_x, target_center_y = self.rectangleScaling(x1, y1, x2, y2)
            
            # Apply aim offset to target center
            target_center_x += aimOffsetX
            target_center_y += aimOffsetY
            
            # ALWAYS DRAW RED TARGET CIRCLE WHEN COLOR IS DETECTED
            cv2.circle(final, (target_center_x, target_center_y), 8, (0, 0, 255), 2)
            
            # PERFECT LOCK: Direct movement to target center
            rx, ry = self.perfect_target_lock(target_center_x, target_center_y, speedX, speedY)

            # Apply manual override percentage
            if manualOveride and button_9 > 0:
                reduction_factor = (100 - manualOverridePercentage) / 100.0
                rx = rx * reduction_factor
                ry = ry * reduction_factor

            # Draw additional lock visuals only when aim button is pressed
            if button_7 > 0:
                crosshair_center_x, crosshair_center_y = 960, 540
                
                # Draw crosshair circle (GREEN)
                cv2.circle(final, (crosshair_center_x, crosshair_center_y), 8, (0, 255, 0), 2)
                
                # Draw LOCK indicator line
                cv2.line(final, (crosshair_center_x, crosshair_center_y), 
                        (target_center_x, target_center_y), (0, 255, 0), 2)
                
                # Draw lock status
                distance = ((target_center_x - crosshair_center_x) ** 2 + 
                          (target_center_y - crosshair_center_y) ** 2) ** 0.5
                
                if distance < 3:
                    lock_status = "PERFECT LOCK"
                    lock_color = (0, 255, 0)  # Green
                else:
                    lock_status = "LOCKING"
                    lock_color = (0, 255, 255)  # Yellow
                
                cv2.putText(final, lock_status, 
                          (crosshair_center_x - 50, crosshair_center_y - 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, lock_color, 2)
                
                cv2.putText(final, f"Dist: {int(distance)}px", 
                          (crosshair_center_x - 40, crosshair_center_y - 40), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            else:
                # Show detection status when not aiming
                crosshair_center_x, crosshair_center_y = 960, 540
                cv2.putText(final, "TARGET DETECTED", 
                          (crosshair_center_x - 60, crosshair_center_y - 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return (final, rx, ry)

    def process(self, frame, gcvdata):
        button_5 = gtuner.get_actual(gtuner.BUTTON_5)
        button_7 = gtuner.get_actual(gtuner.BUTTON_7)
        button_9 = gtuner.get_actual(gtuner.BUTTON_9)
    
        watermark_text = "F4Vision Enhanced"
        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = 1
        thickness = 1
        color = (0, 0, 0)

        text_size = cv2.getTextSize(watermark_text, font, font_scale, thickness)[0]
        text_x = (1920 - text_size[0]) // 2
        text_y = text_size[1] + 10

        cv2.putText(frame, watermark_text, (text_x, text_y), font, font_scale, color, thickness)
    
        frame_process, rightStickX, rightStickY = self.predict(frame, button_5, button_7, button_9)
    
        # Stick movement data
        gcvdata.extend(int(float(rightStickX) * 0x10000).to_bytes(4, byteorder="big", signed=True))
        gcvdata.extend(int(float(rightStickY) * 0x10000).to_bytes(4, byteorder="big", signed=True))

        # NEW: Append selected Aim Key numeric ID
        aim_button_id = self.get_aim_button_id()
        gcvdata.extend(int(aim_button_id).to_bytes(2, byteorder="big", signed=False))
    
        # DEBUG: Log what we're sending
        self.log(f"GCV DATA DEBUG: Sending aim_button_id = {aim_button_id} to GPC")
    
        return frame_process, gcvdata

def PyInit_F4Visioncv_helper():
    return None