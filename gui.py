import sys
import os
import re
import json
import time
import requests
import hashlib
import uuid
import platform
import subprocess
import traceback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QLabel, QSlider, QPushButton, QTabWidget, QCheckBox,
                             QComboBox, QMessageBox, QFrame, QSplashScreen, QLineEdit,
                             QProgressBar, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient, QPixmap, QPainterPath

class MachineLock:
    @staticmethod
    def get_machine_id():
        """Generate a unique machine ID based on hardware characteristics"""
        try:
            # Get system information
            system_info = ""
            
            # Windows-specific machine ID (uses WMIC)
            if platform.system() == "Windows":
                try:
                    # Get CPU ID
                    cpu_info = subprocess.check_output(
                        'wmic cpu get ProcessorId', 
                        shell=True, 
                        stderr=subprocess.DEVNULL
                    ).decode()
                    cpu_id = re.search(r'([A-F0-9]{8,})', cpu_info)
                    if cpu_id:
                        system_info += cpu_id.group(1)
                except:
                    pass
                
                try:
                    # Get motherboard serial
                    baseboard_info = subprocess.check_output(
                        'wmic baseboard get serialnumber', 
                        shell=True, 
                        stderr=subprocess.DEVNULL
                    ).decode()
                    baseboard_serial = re.search(r'([A-Z0-9]{4,})', baseboard_info)
                    if baseboard_serial:
                        system_info += baseboard_serial.group(1)
                except:
                    pass
                
                try:
                    # Get disk serial
                    disk_info = subprocess.check_output(
                        'wmic diskdrive get serialnumber', 
                        shell=True, 
                        stderr=subprocess.DEVNULL
                    ).decode()
                    disk_serial = re.search(r'([A-Z0-9]{4,})', disk_info)
                    if disk_serial:
                        system_info += disk_serial.group(1)
                except:
                    pass
            
            # Fallback for non-Windows or if WMIC fails
            if not system_info:
                system_info = platform.node() + platform.processor() + platform.machine()
            
            # Generate hash from system info
            machine_hash = hashlib.sha256(system_info.encode()).hexdigest()[:32]
            return machine_hash
            
        except Exception as e:
            # Ultimate fallback - generate random ID (less secure)
            print(f"Warning: Could not generate hardware ID: {e}")
            return str(uuid.uuid4())
    
    @staticmethod
    def save_machine_id():
        """Save machine ID to file for persistence"""
        machine_id = MachineLock.get_machine_id()
        try:
            with open("machine_id.txt", "w") as f:
                f.write(machine_id)
            return machine_id
        except Exception as e:
            print(f"Error saving machine ID: {e}")
            return machine_id
    
    @staticmethod
    def load_machine_id():
        """Load machine ID from file"""
        try:
            with open("machine_id.txt", "r") as f:
                return f.read().strip()
        except:
            return MachineLock.save_machine_id()

class VerificationThread(QThread):
    verification_result = pyqtSignal(dict)
    
    def __init__(self, discord_id, api_url, machine_id):
        super().__init__()
        self.discord_id = discord_id
        self.api_url = api_url
        self.machine_id = machine_id
    
    def run(self):
        try:
            # Send verification request with machine ID
            payload = {
                'discordId': self.discord_id,
                'machineId': self.machine_id
            }
            
            response = requests.post(
                f"{self.api_url}/api/verify", 
                json=payload,
                timeout=10
            )
            self.verification_result.emit(response.json())
        except Exception as e:
            self.verification_result.emit({
                'success': False,
                'error': f'Connection error: {str(e)}'
            })

class SplashScreen(QSplashScreen):
    def __init__(self):
        # Create a transparent pixmap for the splash screen
        pixmap = QPixmap(600, 500)
        pixmap.fill(Qt.GlobalColor.transparent)  # Transparent background
        
        super().__init__(pixmap)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setEnabled(False)
        
        # Center on screen
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move((screen_geometry.width() - self.width()) // 2, 
                  (screen_geometry.height() - self.height()) // 2)
    
    def drawContents(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        try:
            logo_path = os.path.join("UI", "logo.png")
            logo_pixmap = QPixmap(logo_path)
            if not logo_pixmap.isNull():
                # Scale logo to fit nicely (adjust size as needed)
                logo_pixmap = logo_pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # Calculate position to center the logo
                logo_x = (self.width() - logo_pixmap.width()) // 2
                logo_y = 70
                painter.drawPixmap(logo_x, logo_y, logo_pixmap)
            else:
                self.draw_placeholder_logo(painter)
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.draw_placeholder_logo(painter)
    
    def draw_placeholder_logo(self, painter):
        """Draw placeholder logo if actual logo.png is not found"""
        logo_rect = QPainterPath()
        logo_rect.addRoundedRect(100, 60, 200, 150, 20, 20)
        
        logo_gradient = QLinearGradient(100, 60, 300, 210)
        logo_gradient.setColorAt(0, QColor(160, 32, 240))
        logo_gradient.setColorAt(1, QColor(138, 0, 255))
        painter.fillPath(logo_rect, logo_gradient)
        
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.drawText(100, 60, 200, 150, Qt.AlignmentFlag.AlignCenter, "F4V")

class CompactSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal):
        super().__init__(orientation)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #4A5568;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #A020F0;
                border: 2px solid #FFFFFF;
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #8A00FF;
            }
            QSlider::sub-page:horizontal {
                background: #A020F0;
                border-radius: 2px;
            }
        """)

class CompactButton(QPushButton):
    def __init__(self, text, primary=False, accent=False, size="medium"):
        super().__init__(text)
        
        if size == "small":
            padding = "6px 12px"
            font_size = "10px"
            radius = "4px"
        elif size == "large":
            padding = "10px 20px"
            font_size = "12px"
            radius = "6px"
        else:  # medium
            padding = "8px 16px"
            font_size = "11px"
            radius = "5px"
            
        if primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #A020F0;
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: {radius};
                    font-weight: 600;
                    font-size: {font_size};
                }}
                QPushButton:hover {{
                    background: #8A00FF;
                }}
                QPushButton:pressed {{
                    background: #7A00E0;
                }}
                QPushButton:disabled {{
                    background: #4A5568;
                    color: #718096;
                }}
            """)
        elif accent:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #8A00FF;
                    color: white;
                    border: none;
                    padding: {padding};
                    border-radius: {radius};
                    font-weight: 600;
                    font-size: {font_size};
                }}
                QPushButton:hover {{
                    background: #7A00E0;
                }}
                QPushButton:pressed {{
                    background: #6A00C0;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #2D3748;
                    color: #E2E8F0;
                    border: 1px solid #4A5568;
                    padding: {padding};
                    border-radius: {radius};
                    font-weight: 600;
                    font-size: {font_size};
                }}
                QPushButton:hover {{
                    background: #4A5568;
                }}
                QPushButton:pressed {{
                    background: #1A202C;
                }}
            """)

class CompactGroupBox(QGroupBox):
    def __init__(self, title=""):
        super().__init__(title)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #4A5568;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: #2D3748;
                color: #E2E8F0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 2px 8px;
                color: #E2E8F0;
                background-color: #A020F0;
                border-radius: 3px;
            }
        """)

class CompactLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2D3748;
                border: 1px solid #4A5568;
                border-radius: 4px;
                padding: 8px 10px;
                color: #E2E8F0;
                font-size: 11px;
                selection-background-color: #A020F0;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1px solid #A020F0;
            }
            QLineEdit::placeholder {
                color: #718096;
                font-style: italic;
            }
        """)

class CompactComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QComboBox {
                background-color: #2D3748;
                border: 1px solid #4A5568;
                border-radius: 4px;
                padding: 6px 8px;
                color: #E2E8F0;
                min-width: 100px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid #E2E8F0;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D3748;
                border: 1px solid #4A5568;
                color: #E2E8F0;
                selection-background-color: #A020F0;
                outline: none;
            }
            QComboBox:hover {
                border: 1px solid #718096;
            }
        """)

class ProfileManager:
    def __init__(self):
        self.profiles_directory = r"C:\GtunerIV\scripts\F4Vision-main\dataset\profiles"
        self.control_file = "profile_control.json"
        self.ensure_profiles_directory()
    
    def ensure_profiles_directory(self):
        """Create profiles directory if it doesn't exist"""
        if not os.path.exists(self.profiles_directory):
            os.makedirs(self.profiles_directory)
            print(f"Created profiles directory: {self.profiles_directory}")
    
    def get_profile_list(self):
        """Get list of all profile files"""
        profiles = []
        try:
            if os.path.exists(self.profiles_directory):
                for file in os.listdir(self.profiles_directory):
                    if file.endswith('.json'):
                        profile_name = file[:-5]  # Remove .json extension
                        profiles.append(profile_name)
            return sorted(profiles)
        except Exception as e:
            print(f"Error getting profile list: {e}")
            return []
    
    def create_profile(self, profile_name):
        """Create a new profile with current settings"""
        try:
            profile_path = os.path.join(self.profiles_directory, f"{profile_name}.json")
            
            # Read current settings from settings.py
            current_settings = self.read_current_settings()
            
            # Save to profile file
            with open(profile_path, 'w') as f:
                json.dump(current_settings, f, indent=2)
            
            print(f"Profile created: {profile_name}")
            return True
            
        except Exception as e:
            print(f"Error creating profile: {e}")
            return False
    
    def delete_profile(self, profile_name):
        """Delete a profile"""
        try:
            profile_path = os.path.join(self.profiles_directory, f"{profile_name}.json")
            if os.path.exists(profile_path):
                os.remove(profile_path)
                print(f"Profile deleted: {profile_name}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
    def load_profile(self, profile_name):
        """Load settings from a profile into settings.py"""
        try:
            profile_path = os.path.join(self.profiles_directory, f"{profile_name}.json")
            
            if not os.path.exists(profile_path):
                return False
            
            # Read profile settings
            with open(profile_path, 'r') as f:
                profile_settings = json.load(f)
            
            # Apply settings to settings.py
            self.apply_settings_to_file(profile_settings)
            
            print(f"Profile loaded: {profile_name}")
            return True
            
        except Exception as e:
            print(f"Error loading profile: {e}")
            return False
    
    def save_current_to_profile(self, profile_name):
        """Save current settings to an existing profile"""
        try:
            profile_path = os.path.join(self.profiles_directory, f"{profile_name}.json")
            
            # Read current settings
            current_settings = self.read_current_settings()
            
            # Save to profile file
            with open(profile_path, 'w') as f:
                json.dump(current_settings, f, indent=2)
            
            print(f"Settings saved to profile: {profile_name}")
            return True
            
        except Exception as e:
            print(f"Error saving to profile: {e}")
            return False
    
    def read_current_settings(self):
        """Read current settings from settings.py"""
        settings = {}
        try:
            with open("settings.py", 'r') as f:
                content = f.read()
            
            # Extract all relevant settings
            settings['boundingBoxWidth'] = self.extract_setting(content, 'boundingBoxWidth', int, 720)
            settings['boundingBoxHeight'] = self.extract_setting(content, 'boundingBoxHeight', int, 480)
            settings['speedX'] = self.extract_setting(content, 'speedX', int, 9)
            settings['speedY'] = self.extract_setting(content, 'speedY', int, 9)
            settings['colorConfidence'] = self.extract_setting(content, 'colorConfidence', float, 0.7)
            settings['aimOffsetX'] = self.extract_setting(content, 'aimOffsetX', int, 0)
            settings['aimOffsetY'] = self.extract_setting(content, 'aimOffsetY', int, 0)
            settings['aimSmoothing'] = self.extract_setting(content, 'aimSmoothing', bool, False)
            settings['smoothAimFactor'] = self.extract_setting(content, 'smoothAimFactor', float, 0.0)
            settings['aimActivationButton'] = self.extract_setting(content, 'aimActivationButton', str, 'BUTTON_7')
            
            return settings
            
        except Exception as e:
            print(f"Error reading current settings: {e}")
            return {}
    
    def extract_setting(self, content, setting_name, value_type, default):
        """Extract a specific setting from settings.py content"""
        try:
            if value_type == bool:
                pattern = rf'{setting_name}\s*=\s*(True|False)'
                match = re.search(pattern, content)
                if match:
                    return match.group(1) == 'True'
            elif value_type == int:
                pattern = rf'{setting_name}\s*=\s*(\d+)'
                match = re.search(pattern, content)
                if match:
                    return int(match.group(1))
            elif value_type == float:
                pattern = rf'{setting_name}\s*=\s*([0-9.]+)'
                match = re.search(pattern, content)
                if match:
                    return float(match.group(1))
            elif value_type == str:
                pattern = rf'{setting_name}\s*=\s*"([^"]+)"'
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
        except:
            pass
        return default
    
    def apply_settings_to_file(self, settings):
        """Apply settings dictionary to settings.py file"""
        try:
            with open("settings.py", 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            settings_applied = {key: False for key in settings.keys()}
            
            for line in lines:
                stripped_line = line.strip()
                
                if not stripped_line:
                    new_lines.append(line)
                    continue
                
                line_updated = False
                for setting_name, setting_value in settings.items():
                    if stripped_line.startswith(setting_name):
                        if isinstance(setting_value, bool):
                            new_lines.append(f'{setting_name} = {str(setting_value)}\n')
                        elif isinstance(setting_value, float):
                            new_lines.append(f'{setting_name} = {setting_value:.2f}\n')
                        elif isinstance(setting_value, str):
                            new_lines.append(f'{setting_name} = "{setting_value}"\n')
                        else:
                            new_lines.append(f'{setting_name} = {setting_value}\n')
                        settings_applied[setting_name] = True
                        line_updated = True
                        break
                
                if not line_updated:
                    new_lines.append(line)
            
            # Add any missing settings
            for setting_name, setting_value in settings.items():
                if not settings_applied[setting_name]:
                    if isinstance(setting_value, bool):
                        new_lines.append(f'{setting_name} = {str(setting_value)}\n')
                    elif isinstance(setting_value, float):
                        new_lines.append(f'{setting_name} = {setting_value:.2f}\n')
                    elif isinstance(setting_value, str):
                        new_lines.append(f'{setting_name} = "{setting_value}"\n')
                    else:
                        new_lines.append(f'{setting_name} = {setting_value}\n')
            
            # Write back to file
            with open("settings.py", 'w') as f:
                f.writelines(new_lines)
                
            print("Settings applied to settings.py")
            
        except Exception as e:
            print(f"Error applying settings to file: {e}")
    
    def save_active_profile(self, profile_name):
        """Save the currently active profile to control file"""
        try:
            control_data = {
                'active_profile': profile_name,
                'last_updated': time.time(),
                'version': '1.0'
            }
            
            with open(self.control_file, 'w') as f:
                json.dump(control_data, f, indent=2)
            
            print(f"Active profile saved: {profile_name}")
            return True
            
        except Exception as e:
            print(f"Error saving active profile: {e}")
            return False
    
    def load_active_profile(self):
        """Load the previously active profile from control file"""
        try:
            if os.path.exists(self.control_file):
                with open(self.control_file, 'r') as f:
                    control_data = json.load(f)
                
                active_profile = control_data.get('active_profile')
                if active_profile:
                    # Check if the profile still exists
                    profile_path = os.path.join(self.profiles_directory, f"{active_profile}.json")
                    if os.path.exists(profile_path):
                        print(f"Loading previously active profile: {active_profile}")
                        return active_profile
                    else:
                        print(f"Previously active profile not found: {active_profile}")
                        self.cleanup_control_file()
            return None
            
        except Exception as e:
            print(f"Error loading active profile: {e}")
            self.cleanup_control_file()
            return None
    
    def cleanup_control_file(self):
        """Remove corrupted or invalid control file"""
        try:
            if os.path.exists(self.control_file):
                os.remove(self.control_file)
                print("Cleaned up invalid profile control file")
        except Exception as e:
            print(f"Error cleaning up profile control file: {e}")

class PXDManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.pxd_directory = r"C:\GtunerIV\scripts\F4Vision-main\dataset\pxd"
        self.weights_directory = r"C:\GtunerIV\scripts\F4Vision-main\dataset\weights"
        self.current_pxd_file = None
        self.current_weights_file = None
        self.is_pxd_loaded = False
        self.is_weights_loaded = False
        
        # Control files for persistence
        self.pxd_control_file = "pxd_control.json"
        self.weights_control_file = "weights_control.json"
        
        # Load previous state
        self.load_previous_state()
    
    def load_previous_state(self):
        """Load the previously loaded PXD and Weights file states if they exist"""
        # Load PXD state
        try:
            if os.path.exists(self.pxd_control_file):
                with open(self.pxd_control_file, 'r') as f:
                    control_data = json.load(f)
                
                loaded_file = control_data.get('active_pxd_file')
                if loaded_file:
                    # Check if the file still exists
                    file_path = os.path.join(self.pxd_directory, loaded_file)
                    if os.path.exists(file_path):
                        self.current_pxd_file = loaded_file
                        self.is_pxd_loaded = True
                        print(f"Auto-loaded previous PXD file: {loaded_file}")
                    else:
                        print(f"Previously loaded PXD file not found: {loaded_file}")
                        self.cleanup_pxd_control_file()
            else:
                print("No previous PXD state found")
                
        except Exception as e:
            print(f"Error loading previous PXD state: {e}")
            self.cleanup_pxd_control_file()
        
        # Load Weights state
        try:
            if os.path.exists(self.weights_control_file):
                with open(self.weights_control_file, 'r') as f:
                    control_data = json.load(f)
                
                loaded_file = control_data.get('active_weights_file')
                if loaded_file:
                    # Check if the file still exists
                    file_path = os.path.join(self.weights_directory, loaded_file)
                    if os.path.exists(file_path):
                        self.current_weights_file = loaded_file
                        self.is_weights_loaded = True
                        print(f"Auto-loaded previous Weights file: {loaded_file}")
                    else:
                        print(f"Previously loaded Weights file not found: {loaded_file}")
                        self.cleanup_weights_control_file()
            else:
                print("No previous Weights state found")
                
        except Exception as e:
            print(f"Error loading previous Weights state: {e}")
            self.cleanup_weights_control_file()
    
    def cleanup_pxd_control_file(self):
        """Remove corrupted or invalid PXD control file"""
        try:
            if os.path.exists(self.pxd_control_file):
                os.remove(self.pxd_control_file)
                print("Cleaned up invalid PXD control file")
        except Exception as e:
            print(f"Error cleaning up PXD control file: {e}")
    
    def cleanup_weights_control_file(self):
        """Remove corrupted or invalid Weights control file"""
        try:
            if os.path.exists(self.weights_control_file):
                os.remove(self.weights_control_file)
                print("Cleaned up invalid Weights control file")
        except Exception as e:
            print(f"Error cleaning up Weights control file: {e}")
    
    def load_pxd_files(self):
        """Load PXD files into a list"""
        pxd_files = []
        try:
            if os.path.exists(self.pxd_directory):
                files = [f for f in os.listdir(self.pxd_directory) if f.endswith('.pxd')]
                pxd_files = sorted(files)
                print(f"Found {len(pxd_files)} PXD files")
            else:
                print(f"PXD directory not found: {self.pxd_directory}")
                
        except Exception as e:
            print(f"Error loading PXD files: {e}")
            
        return pxd_files
    
    def load_weights_files(self):
        """Load Weights files into a list"""
        weights_files = []
        try:
            if os.path.exists(self.weights_directory):
                # Common weights file extensions
                valid_extensions = ['.pt', '.pth', '.weights', '.onnx', '.bin']
                files = [f for f in os.listdir(self.weights_directory) 
                        if any(f.endswith(ext) for ext in valid_extensions)]
                weights_files = sorted(files)
                print(f"Found {len(weights_files)} Weights files")
            else:
                print(f"Weights directory not found: {self.weights_directory}")
                
        except Exception as e:
            print(f"Error loading Weights files: {e}")
            
        return weights_files
    
    def load_pxd_file(self, filename):
        """Load the selected PXD file for F4Vision to use"""
        if not filename:
            return False, "No file selected"
        
        try:
            # Create a persistent settings file
            settings = {
                'active_pxd_file': filename,
                'pxd_directory': self.pxd_directory,
                'loaded_at': time.time(),
                'version': '1.0'
            }
            
            # Write to control file
            with open(self.pxd_control_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.current_pxd_file = filename
            self.is_pxd_loaded = True
            
            print(f"PXD file loaded: {filename}")
            return True, f"Successfully loaded: {filename}"
            
        except Exception as e:
            error_msg = f"Failed to load PXD file: {str(e)}"
            print(f"Error loading PXD file: {e}")
            return False, error_msg
    
    def load_weights_file(self, filename):
        """Load the selected Weights file for F4Vision to use"""
        if not filename:
            return False, "No file selected"
        
        try:
            # Create a persistent settings file
            settings = {
                'active_weights_file': filename,
                'weights_directory': self.weights_directory,
                'loaded_at': time.time(),
                'version': '1.0'
            }
            
            # Write to control file
            with open(self.weights_control_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.current_weights_file = filename
            self.is_weights_loaded = True
            
            print(f"Weights file loaded: {filename}")
            return True, f"Successfully loaded: {filename}"
            
        except Exception as e:
            error_msg = f"Failed to load Weights file: {str(e)}"
            print(f"Error loading Weights file: {e}")
            return False, error_msg
    
    def unload_pxd_file(self):
        """Unload the current PXD file"""
        try:
            # Clear the control file
            if os.path.exists(self.pxd_control_file):
                os.remove(self.pxd_control_file)
            
            self.is_pxd_loaded = False
            self.current_pxd_file = None
            
            print("PXD file unloaded")
            return True, "PXD file unloaded"
            
        except Exception as e:
            error_msg = f"Failed to unload PXD file: {str(e)}"
            print(f"Error unloading PXD file: {e}")
            return False, error_msg
    
    def unload_weights_file(self):
        """Unload the current Weights file"""
        try:
            # Clear the control file
            if os.path.exists(self.weights_control_file):
                os.remove(self.weights_control_file)
            
            self.is_weights_loaded = False
            self.current_weights_file = None
            
            print("Weights file unloaded")
            return True, "Weights file unloaded"
            
        except Exception as e:
            error_msg = f"Failed to unload Weights file: {str(e)}"
            print(f"Error unloading Weights file: {e}")
            return False, error_msg

class AimConfigWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.setWindowTitle("Aim Configuration - F4Vision")
        self.setGeometry(400, 400, 450, 380)
        
        # Load saved aim settings
        (self.speed, self.color_confidence) = self.load_saved_aim_settings()
        
        self.setStyleSheet("""
            QMainWindow {
                background: #1A202C;
                color: #E2E8F0;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Aim Configuration")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 8px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        # Aim Speed Group
        speed_group = CompactGroupBox("Aim Speed")
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setSpacing(6)
        
        speed_value_layout = QHBoxLayout()
        speed_value_layout.addWidget(QLabel("Speed:"))
        self.speed_label = QLabel(str(self.speed))
        self.speed_label.setStyleSheet("color: #A020F0; font-weight: 600; font-size: 11px;")
        speed_value_layout.addWidget(self.speed_label)
        speed_value_layout.addStretch()
        speed_layout.addLayout(speed_value_layout)
        
        self.speed_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(self.speed)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        
        layout.addWidget(speed_group)
        
        # Color Confidence Group
        color_conf_group = CompactGroupBox("Color Confidence")
        color_conf_layout = QVBoxLayout(color_conf_group)
        color_conf_layout.setSpacing(6)
        
        color_conf_value_layout = QHBoxLayout()
        color_conf_value_layout.addWidget(QLabel("Confidence:"))
        self.color_conf_label = QLabel(f"{self.color_confidence:.2f}")
        self.color_conf_label.setStyleSheet("color: #A020F0; font-weight: 600; font-size: 11px;")
        color_conf_value_layout.addWidget(self.color_conf_label)
        color_conf_value_layout.addStretch()
        color_conf_layout.addLayout(color_conf_value_layout)
        
        self.color_conf_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.color_conf_slider.setRange(10, 100)
        self.color_conf_slider.setValue(int(self.color_confidence * 100))
        self.color_conf_slider.valueChanged.connect(self.on_color_conf_changed)
        color_conf_layout.addWidget(self.color_conf_slider)
        
        layout.addWidget(color_conf_group)
        
        # Reset button
        reset_btn = CompactButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
        # Save timer
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_aim_settings)
        
        self.speed_slider.valueChanged.connect(self.schedule_save)
        self.color_conf_slider.valueChanged.connect(self.schedule_save)
        
    def load_saved_aim_settings(self):
        """Load saved aim settings from settings.py"""
        try:
            with open("settings.py", 'r') as f:
                content = f.read()
            
            speed_x_match = re.search(r'speedX\s*=\s*(\d+)', content)
            speed = int(speed_x_match.group(1)) if speed_x_match else 9
            
            color_conf_match = re.search(r'colorConfidence\s*=\s*([0-9.]+)', content)
            color_confidence = float(color_conf_match.group(1)) if color_conf_match else 0.7
            
            print(f"Loaded aim settings: speed={speed}, colorConfidence={color_confidence}")
            return speed, color_confidence
            
        except Exception as e:
            print(f"Error loading aim settings: {e}")
            return 9, 0.7

    def on_speed_changed(self, value):
        self.speed = value
        self.speed_label.setText(str(value))
        
    def on_color_conf_changed(self, value):
        self.color_confidence = value / 100.0
        self.color_conf_label.setText(f"{self.color_confidence:.2f}")
        
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.speed_slider.setValue(80)
        self.color_conf_slider.setValue(85)
        
    def schedule_save(self):
        """Schedule settings save"""
        self.save_timer.start(100)
        if self.parent_gui:
            self.parent_gui.schedule_auto_save()
        
    def save_aim_settings(self):
        """Save aim settings to settings.py"""
        try:
            with open("settings.py", 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            speed_x_found = speed_y_found = color_conf_found = False
            aim_smoothing_found = smooth_aim_found = False
            
            for line in lines:
                stripped_line = line.strip()
                
                if not stripped_line:
                    new_lines.append(line)
                    continue
                    
                if stripped_line.startswith('speedX'):
                    if not speed_x_found:
                        new_lines.append(f'speedX = {self.speed}\n')
                        speed_x_found = True
                    continue
                    
                elif stripped_line.startswith('speedY'):
                    if not speed_y_found:
                        new_lines.append(f'speedY = {self.speed}\n')
                        speed_y_found = True
                    continue
                    
                elif stripped_line.startswith('colorConfidence'):
                    if not color_conf_found:
                        new_lines.append(f'colorConfidence = {self.color_confidence:.2f}\n')
                        color_conf_found = True
                    continue
                    
                elif stripped_line.startswith('aimSmoothing'):
                    if not aim_smoothing_found:
                        new_lines.append('aimSmoothing = False\n')
                        aim_smoothing_found = True
                    continue
                    
                elif stripped_line.startswith('smoothAimFactor'):
                    if not smooth_aim_found:
                        new_lines.append('smoothAimFactor = 0.0\n')
                        smooth_aim_found = True
                    continue
                    
                else:
                    new_lines.append(line)
            
            if not speed_x_found:
                new_lines.append(f'speedX = {self.speed}\n')
            if not speed_y_found:
                new_lines.append(f'speedY = {self.speed}\n')
            if not color_conf_found:
                new_lines.append(f'colorConfidence = {self.color_confidence:.2f}\n')
            if not aim_smoothing_found:
                new_lines.append('aimSmoothing = False\n')
            if not smooth_aim_found:
                new_lines.append('smoothAimFactor = 0.0\n')
            
            with open("settings.py", 'w') as f:
                f.writelines(new_lines)
                
            print(f"Aim settings saved: speed={self.speed}, colorConfidence={self.color_confidence:.2f}")
            
        except Exception as e:
            print(f"Error saving aim settings: {e}")

class OffsetWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.setWindowTitle("Aim Offset - F4Vision")
        self.setGeometry(400, 400, 400, 350)
        
        # Load saved offset values
        self.offset_x, self.offset_y = self.load_saved_offsets()
        
        self.setStyleSheet("""
            QMainWindow {
                background: #1A202C;
                color: #E2E8F0;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Aim Offset Calibration")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #8A00FF; 
            padding: 8px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        # Crosshair display
        crosshair_frame = QFrame()
        crosshair_frame.setStyleSheet("""
            QFrame {
                background-color: #2D3748;
                border-radius: 4px;
                border: 1px solid #4A5568;
            }
        """)
        crosshair_layout = QVBoxLayout(crosshair_frame)
        crosshair_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.crosshair_widget = CrosshairWidget(self.offset_x, self.offset_y)
        self.crosshair_widget.setFixedSize(300, 150)
        crosshair_layout.addWidget(self.crosshair_widget)
        
        layout.addWidget(crosshair_frame)
        
        # Offset controls
        controls_group = CompactGroupBox("Offset Controls")
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setSpacing(8)
        
        # Horizontal offset
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("X:"))
        
        self.h_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.h_slider.setRange(-100, 100)
        self.h_slider.setValue(self.offset_x)
        self.h_slider.valueChanged.connect(self.on_h_offset_changed)
        h_layout.addWidget(self.h_slider)
        
        self.h_label = QLabel(str(self.offset_x))
        self.h_label.setFixedWidth(30)
        self.h_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_label.setStyleSheet("""
            color: #8A00FF; 
            font-weight: 600; 
            font-size: 10px;
            background-color: #2D3748;
            border-radius: 3px;
            padding: 2px;
            border: 1px solid #8A00FF;
        """)
        h_layout.addWidget(self.h_label)
        
        controls_layout.addLayout(h_layout)
        
        # Vertical offset
        v_layout = QHBoxLayout()
        v_layout.addWidget(QLabel("Y:"))
        
        self.v_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.v_slider.setRange(-100, 100)
        self.v_slider.setValue(self.offset_y)
        self.v_slider.valueChanged.connect(self.on_v_offset_changed)
        v_layout.addWidget(self.v_slider)
        
        self.v_label = QLabel(str(self.offset_y))
        self.v_label.setFixedWidth(30)
        self.v_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v_label.setStyleSheet("""
            color: #8A00FF; 
            font-weight: 600; 
            font-size: 10px;
            background-color: #2D3748;
            border-radius: 3px;
            padding: 2px;
            border: 1px solid #8A00FF;
        """)
        v_layout.addWidget(self.v_label)
        
        controls_layout.addLayout(v_layout)
        
        # Current offset display
        self.offset_label = QLabel(f"Offset: X={self.offset_x}, Y={self.offset_y}")
        self.offset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.offset_label.setStyleSheet("""
            background-color: rgba(138, 0, 255, 0.1); 
            padding: 6px; 
            border-radius: 3px; 
            font-weight: 600; 
            color: #8A00FF;
            border: 1px solid #8A00FF;
            font-size: 10px;
        """)
        controls_layout.addWidget(self.offset_label)
        
        # Reset button
        reset_btn = CompactButton("Reset Offset")
        reset_btn.clicked.connect(self.reset_offset)
        controls_layout.addWidget(reset_btn)
        
        layout.addWidget(controls_group)
        
        layout.addStretch()
        
        # Save timer
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_offset)
        
        self.h_slider.valueChanged.connect(self.schedule_save)
        self.v_slider.valueChanged.connect(self.schedule_save)
        
    def load_saved_offsets(self):
        """Load saved offset values from settings.py"""
        try:
            with open("settings.py", 'r') as f:
                content = f.read()
            
            x_match = re.search(r'aimOffsetX\s*=\s*(-?\d+)', content)
            offset_x = int(x_match.group(1)) if x_match else 0
            
            y_match = re.search(r'aimOffsetY\s*=\s*(-?\d+)', content)
            offset_y = int(y_match.group(1)) if y_match else 0
            
            print(f"Loaded saved offsets: X={offset_x}, Y={offset_y}")
            return offset_x, offset_y
            
        except Exception as e:
            print(f"Error loading saved offsets: {e}")
            return 0, 0

    def on_h_offset_changed(self, value):
        self.offset_x = value
        self.h_label.setText(str(value))
        self.crosshair_widget.set_offset(value, self.offset_y)
        self.offset_label.setText(f"Offset: X={value}, Y={self.offset_y}")
        
    def on_v_offset_changed(self, value):
        self.offset_y = value
        self.v_label.setText(str(value))
        self.crosshair_widget.set_offset(self.offset_x, value)
        self.offset_label.setText(f"Offset: X={self.offset_x}, Y={value}")
        
    def reset_offset(self):
        self.h_slider.setValue(0)
        self.v_slider.setValue(0)
        
    def schedule_save(self):
        """Schedule offset save"""
        self.save_timer.start(50)
        if self.parent_gui:
            self.parent_gui.schedule_auto_save()
        
    def save_offset(self):
        """Save offset to settings.py"""
        try:
            with open("settings.py", 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            aim_offset_x_found = aim_offset_y_found = False
            
            for line in lines:
                stripped_line = line.strip()
                
                if not stripped_line:
                    new_lines.append(line)
                    continue
                    
                if stripped_line.startswith('aimOffsetX'):
                    if not aim_offset_x_found:
                        new_lines.append(f'aimOffsetX = {self.offset_x}\n')
                        aim_offset_x_found = True
                    continue
                    
                elif stripped_line.startswith('aimOffsetY'):
                    if not aim_offset_y_found:
                        new_lines.append(f'aimOffsetY = {self.offset_y}\n')
                        aim_offset_y_found = True
                    continue
                    
                else:
                    new_lines.append(line)
            
            if not aim_offset_x_found:
                new_lines.append(f'aimOffsetX = {self.offset_x}\n')
            if not aim_offset_y_found:
                new_lines.append(f'aimOffsetY = {self.offset_y}\n')
            
            with open("settings.py", 'w') as f:
                f.writelines(new_lines)
                
            print(f"Offset saved: {self.offset_x}, {self.offset_y}")
            
        except Exception as e:
            print(f"Error saving offset: {e}")

class CrosshairWidget(QWidget):
    def __init__(self, offset_x=0, offset_y=0):
        super().__init__()
        self.offset_x = offset_x
        self.offset_y = offset_y
        
    def set_offset(self, x, y):
        self.offset_x = x
        self.offset_y = y
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dark background
        painter.fillRect(0, 0, self.width(), self.height(), QColor(45, 55, 72))
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        offset_x = int(center_x + (self.offset_x * 1.0))
        offset_y = int(center_y + (self.offset_y * 1.0))
        
        # Draw center point (original position)
        painter.setBrush(QBrush(QColor(160, 32, 240)))
        painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)
        
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
        
        # Draw crosshair lines
        painter.setPen(QPen(QColor(138, 0, 255), 1))
        painter.drawLine(0, offset_y, self.width(), offset_y)
        painter.drawLine(offset_x, 0, offset_x, self.height())
        
        # Draw offset point
        painter.setBrush(QBrush(QColor(138, 0, 255)))
        painter.drawEllipse(offset_x - 3, offset_y - 3, 6, 6)

class F4VisionSettingsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.settings_file = "settings.py"
        self.api_url = "https://f4vision-bot1-production.up.railway.app"
        self.is_verified = False
        self.current_discord_id = ""
        self.machine_id = ""
        self.profile_manager = ProfileManager()
        self.current_profile = None
        self.pxd_manager = PXDManager(self)
        
        self.load_current_settings()
        
        self.setWindowTitle("F4Vision")
        self.setGeometry(300, 300, 700, 500)
        
        self.setStyleSheet("""
            QMainWindow {
                background: #1A202C;
                color: #E2E8F0;
                font-family: 'Segoe UI';
            }
            QTabWidget::pane {
                border: 1px solid #4A5568;
                background-color: #2D3748;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2D3748;
                color: #A0AEC0;
                padding: 8px 12px;
                margin: 1px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #A020F0;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #4A5568;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI';
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: #A020F0;
                border-radius: 6px;
                padding: 3px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 6, 12, 6)
        
        header_label = QLabel("F4VISION")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: 700; 
            color: #FFFFFF; 
            padding: 4px;
        """)
        header_layout.addWidget(header_label)
        
        version_label = QLabel("v2.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        version_label.setStyleSheet("""
            font-size: 9px; 
            font-weight: 600; 
            color: #FFFFFF; 
            background-color: rgba(0, 0, 0, 0.2);
            padding: 2px 6px;
            border-radius: 3px;
        """)
        header_layout.addWidget(version_label)
        
        layout.addWidget(header_frame)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.create_startup_tab()
        self.create_profiles_tab()
        self.create_detection_tab()
        self.create_aim_tab()
        self.create_pxd_tab()
        
        # Disable all tabs except Start Up initially
        self.disable_all_tabs()
        
        # Footer
        footer_label = QLabel("© 2024 F4Vision")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("""
            color: #718096;
            font-size: 9px;
            padding: 4px;
        """)
        layout.addWidget(footer_label)
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_to_profile)
        
        # Load previously active profile
        self.load_previous_profile()
        
    def load_previous_profile(self):
        """Load the previously active profile on startup"""
        active_profile = self.profile_manager.load_active_profile()
        if active_profile:
            index = self.profile_combo.findText(active_profile)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
                print(f"Auto-loaded previous profile: {active_profile}")
        
    def enable_all_tabs(self):
        """Enable all tabs after successful verification"""
        for i in range(self.tab_widget.count()):
            if i != 0:
                self.tab_widget.setTabEnabled(i, True)

    def disable_all_tabs(self):
        """Disable all tabs except Start Up"""
        for i in range(self.tab_widget.count()):
            if i != 0:
                self.tab_widget.setTabEnabled(i, False)
        
    def create_startup_tab(self):
        """Create the Start Up tab with Discord ID verification"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title_label = QLabel("Start Up Verification")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 6px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        # Discord ID Verification Group
        verification_group = CompactGroupBox("Discord ID Verification")
        verification_layout = QVBoxLayout(verification_group)
        verification_layout.setSpacing(8)
        
        # Instructions
        instructions = QLabel(
            "To use F4Vision, you need an active subscription.\n\n"
            "1. Purchase subscription using /buy in Discord\n"
            "2. Get Discord ID using /login\n"
            "3. Enter Discord ID below\n"
            "4. Machine locked to one PC\n"
            "5. Use /hwidreset to change machines"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            padding: 8px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-size: 10px;
            line-height: 1.4;
            color: #CBD5E0;
        """)
        verification_layout.addWidget(instructions)
        
        # Discord ID Input
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Discord ID:"))
        
        self.discord_id_input = CompactLineEdit("Enter 18-digit Discord ID")
        self.discord_id_input.textChanged.connect(self.on_discord_id_changed)
        id_layout.addWidget(self.discord_id_input)
        
        verification_layout.addLayout(id_layout)
        
        # Verify Button
        self.verify_btn = CompactButton("Verify Subscription", primary=True)
        self.verify_btn.clicked.connect(self.verify_subscription)
        self.verify_btn.setEnabled(False)
        verification_layout.addWidget(self.verify_btn)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4A5568;
                border-radius: 4px;
                background-color: #2D3748;
                text-align: center;
                color: #E2E8F0;
                height: 12px;
            }
            QProgressBar::chunk {
                background: #A020F0;
                border-radius: 3px;
            }
        """)
        verification_layout.addWidget(self.progress_bar)
        
        # Status Display
        self.verification_status = QLabel("Enter Discord ID to verify")
        self.verification_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verification_status.setStyleSheet("""
            padding: 8px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #4A5568;
            color: #CBD5E0;
        """)
        verification_layout.addWidget(self.verification_status)
        
        # Subscription Details
        self.subscription_details = QLabel()
        self.subscription_details.setVisible(False)
        self.subscription_details.setWordWrap(True)
        self.subscription_details.setStyleSheet("""
            padding: 8px; 
            background-color: rgba(160, 32, 240, 0.1); 
            border-radius: 4px; 
            font-size: 10px;
            line-height: 1.4;
            border: 1px solid #A020F0;
            color: #CBD5E0;
        """)
        verification_layout.addWidget(self.subscription_details)
        
        layout.addWidget(verification_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Start Up")
    
    def on_discord_id_changed(self, text):
        """Enable verify button only when Discord ID looks valid"""
        is_valid = len(text.strip()) >= 17 and text.strip().isdigit()
        self.verify_btn.setEnabled(is_valid)
        
    def verify_subscription(self):
        """Verify Discord ID subscription with machine locking"""
        discord_id = self.discord_id_input.text().strip()
        
        if not discord_id or not discord_id.isdigit():
            self.show_verification_status("❌ Invalid Discord ID", "error")
            return
        
        self.current_discord_id = discord_id
        self.machine_id = MachineLock.load_machine_id()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.verify_btn.setEnabled(False)
        self.show_verification_status("🔍 Verifying...", "verifying")
        
        # Start verification thread
        self.verification_thread = VerificationThread(discord_id, self.api_url, self.machine_id)
        self.verification_thread.verification_result.connect(self.handle_verification_result)
        self.verification_thread.start()

    def handle_verification_result(self, result):
        """Handle the verification response from the API"""
        self.progress_bar.setVisible(False)
        self.verify_btn.setEnabled(True)
        
        if result.get('success'):
            if result.get('hasSubscription'):
                if result.get('machineAllowed', False):
                    user_data = result.get('user', {})
                    plan_name = user_data.get('plan', 'Unknown')
                    days_remaining = user_data.get('daysRemaining', 0)
                    
                    self.is_verified = True
                    self.show_verification_status("✅ Verified!", "success")
                    
                    details_text = (
                        f"Plan: {plan_name}\n"
                        f"Days: {days_remaining}\n"
                        f"ID: {self.current_discord_id}\n"
                        f"Status: 🔒 Machine Locked"
                    )
                    self.subscription_details.setText(details_text)
                    self.subscription_details.setVisible(True)
                    
                    self.enable_all_tabs()
                    
                else:
                    self.show_verification_status("❌ Wrong Machine", "error")
                    details_text = (
                        f"Subscription on different machine.\n"
                        f"Use /hwidreset in Discord."
                    )
                    self.subscription_details.setText(details_text)
                    self.subscription_details.setVisible(True)
                    self.is_verified = False
                    
            else:
                self.show_verification_status("❌ No Subscription", "error")
                self.subscription_details.setVisible(False)
                self.is_verified = False
                
        else:
            error_msg = result.get('error', 'Unknown error')
            self.show_verification_status(f"❌ {error_msg}", "error")
            self.subscription_details.setVisible(False)
            self.is_verified = False
        
        if not self.is_verified:
            self.disable_all_tabs()
    
    def show_verification_status(self, message, status_type):
        """Update verification status display"""
        self.verification_status.setText(message)
        
        if status_type == "success":
            style = """
                padding: 8px; 
                background-color: rgba(160, 32, 240, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #A020F0;
            """
        elif status_type == "error":
            style = """
                padding: 8px; 
                background-color: rgba(244, 67, 54, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #F44336;
            """
        elif status_type == "verifying":
            style = """
                padding: 8px; 
                background-color: rgba(255, 152, 0, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #FF9800;
            """
        else:
            style = """
                padding: 8px; 
                background-color: #2D3748; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #4A5568;
                color: #CBD5E0;
            """
        
        self.verification_status.setStyleSheet(style)
    
    def create_profiles_tab(self):
        """Create the Profiles tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title_label = QLabel("Game Profiles")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 6px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        # Profile Management Group
        profile_group = CompactGroupBox("Profile Management")
        profile_layout = QVBoxLayout(profile_group)
        profile_layout.setSpacing(8)
        
        # Instructions
        instructions = QLabel(
            "Create profiles for different games.\n"
            "Auto-saves settings when changed."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            padding: 6px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-size: 10px;
            line-height: 1.4;
            color: #CBD5E0;
        """)
        profile_layout.addWidget(instructions)
        
        # Profile Selection
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Profile:"))
        
        self.profile_combo = CompactComboBox()
        self.load_profiles()
        self.profile_combo.currentTextChanged.connect(self.on_profile_selected)
        selection_layout.addWidget(self.profile_combo)
        
        # Add/Remove buttons
        button_layout = QHBoxLayout()
        
        self.add_profile_btn = QPushButton("+")
        self.add_profile_btn.setFixedSize(24, 24)
        self.add_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #A020F0;
                color: #FFFFFF;
                border: none;
                border-radius: 3px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #8A00FF;
            }
            QPushButton:pressed {
                background-color: #7A00E0;
            }
        """)
        self.add_profile_btn.clicked.connect(self.add_profile)
        button_layout.addWidget(self.add_profile_btn)
        
        self.remove_profile_btn = QPushButton("-")
        self.remove_profile_btn.setFixedSize(24, 24)
        self.remove_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #8A00FF;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7A00E0;
            }
            QPushButton:pressed {
                background-color: #6A00C0;
            }
            QPushButton:disabled {
                background-color: #4A5568;
                color: #718096;
            }
        """)
        self.remove_profile_btn.clicked.connect(self.remove_profile)
        self.remove_profile_btn.setEnabled(False)
        button_layout.addWidget(self.remove_profile_btn)
        
        selection_layout.addLayout(button_layout)
        profile_layout.addLayout(selection_layout)
        
        # Current Profile Status
        self.profile_status = QLabel("No profile selected")
        self.profile_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_status.setStyleSheet("""
            padding: 6px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #4A5568;
            color: #CBD5E0;
        """)
        profile_layout.addWidget(self.profile_status)
        
        # Auto-save status
        self.auto_save_status = QLabel("Auto-save: Inactive")
        self.auto_save_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auto_save_status.setStyleSheet("""
            padding: 4px; 
            background-color: #2D3748; 
            border-radius: 3px; 
            font-size: 9px;
            color: #718096;
        """)
        profile_layout.addWidget(self.auto_save_status)
        
        layout.addWidget(profile_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Profiles")
    
    def load_profiles(self):
        """Load available profiles into the dropdown"""
        self.profile_combo.clear()
        profiles = self.profile_manager.get_profile_list()
        
        if profiles:
            self.profile_combo.addItem("-- Select Profile --")
            self.profile_combo.addItems(profiles)
        else:
            self.profile_combo.addItem("No profiles found")
    
    def on_profile_selected(self, profile_name):
        """Handle profile selection from dropdown"""
        if (profile_name and 
            profile_name != "-- Select Profile --" and 
            profile_name != "No profiles found"):
            
            self.current_profile = profile_name
            self.remove_profile_btn.setEnabled(True)
            self.profile_status.setText(f"Active: {profile_name}")
            self.profile_status.setStyleSheet("""
                padding: 6px; 
                background-color: rgba(160, 32, 240, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #A020F0;
            """)
            self.auto_save_status.setText("Auto-save: Active")
            self.auto_save_status.setStyleSheet("""
                padding: 4px; 
                background-color: rgba(160, 32, 240, 0.1); 
                border-radius: 3px; 
                font-size: 9px;
                color: #A020F0;
            """)
            
            self.profile_manager.save_active_profile(profile_name)
            
            if self.profile_manager.load_profile(profile_name):
                self.load_current_settings()
                self.refresh_gui_settings()
                print(f"Profile loaded: {profile_name}")
            else:
                self.profile_status.setText(f"Error: {profile_name}")
                self.profile_status.setStyleSheet("""
                    padding: 6px; 
                    background-color: rgba(244, 67, 54, 0.1); 
                    color: #E2E8F0; 
                    border-radius: 4px; 
                    font-weight: 600;
                    font-size: 11px;
                    border: 1px solid #F44336;
                """)
        else:
            self.current_profile = None
            self.remove_profile_btn.setEnabled(False)
            self.profile_status.setText("No profile selected")
            self.profile_status.setStyleSheet("""
                padding: 6px; 
                background-color: #2D3748; 
                border-radius: 4px; 
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #4A5568;
                color: #CBD5E0;
            """)
            self.auto_save_status.setText("Auto-save: Inactive")
            self.auto_save_status.setStyleSheet("""
                padding: 4px; 
                background-color: #2D3748; 
                border-radius: 3px; 
                font-size: 9px;
                color: #718096;
            """)
    
    def add_profile(self):
        """Create a new profile"""
        profile_name, ok = QInputDialog.getText(
            self, 
            "Create Profile", 
            "Profile name:",
            text="MyProfile"
        )
        
        if ok and profile_name:
            if not profile_name.strip():
                QMessageBox.warning(self, "Invalid", "Profile name required.")
                return
            
            existing_profiles = self.profile_manager.get_profile_list()
            if profile_name in existing_profiles:
                QMessageBox.warning(self, "Exists", f"Profile '{profile_name}' exists.")
                return
            
            if self.profile_manager.create_profile(profile_name):
                self.load_profiles()
                self.profile_combo.setCurrentText(profile_name)
                QMessageBox.information(self, "Success", f"Created '{profile_name}'")
            else:
                QMessageBox.critical(self, "Error", "Failed to create profile")
    
    def remove_profile(self):
        """Remove the currently selected profile"""
        if not self.current_profile:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete '{self.current_profile}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.profile_manager.delete_profile(self.current_profile):
                self.load_profiles()
                self.current_profile = None
                self.remove_profile_btn.setEnabled(False)
                self.profile_status.setText("No profile selected")
                self.profile_status.setStyleSheet("""
                    padding: 6px; 
                    background-color: #2D3748; 
                    border-radius: 4px; 
                    font-weight: 600;
                    font-size: 11px;
                    border: 1px solid #4A5568;
                    color: #CBD5E0;
                """)
                self.auto_save_status.setText("Auto-save: Inactive")
                QMessageBox.information(self, "Success", "Profile deleted")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete")
    
    def schedule_auto_save(self):
        """Schedule auto-save to current profile"""
        if self.current_profile:
            self.auto_save_timer.start(500)
    
    def auto_save_to_profile(self):
        """Automatically save current settings to the selected profile"""
        if self.current_profile:
            if self.profile_manager.save_current_to_profile(self.current_profile):
                print(f"Auto-saved to: {self.current_profile}")
    
    def refresh_gui_settings(self):
        """Refresh GUI elements to reflect loaded settings"""
        self.width_slider.setValue(self.bbox_width)
        self.height_slider.setValue(self.bbox_height)
        self.width_label.setText(f"{self.bbox_width} px")
        self.height_label.setText(f"{self.bbox_height} px")
        self.size_label.setText(f"Size: {self.bbox_width} × {self.bbox_height}")
        
        if hasattr(self, 'aim_button_combo'):
            index = self.aim_button_combo.findText(self.aim_activation_button)
            if index >= 0:
                self.aim_button_combo.setCurrentIndex(index)
        
        print("GUI settings refreshed")
        
    def create_detection_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title_label = QLabel("Detection Box")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 6px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        size_group = CompactGroupBox("Box Size")
        size_layout = QVBoxLayout(size_group)
        size_layout.setSpacing(8)
        
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        
        self.width_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(100, 1500)
        self.width_slider.setValue(self.bbox_width)
        self.width_slider.valueChanged.connect(self.on_width_changed)
        width_layout.addWidget(self.width_slider)
        
        self.width_label = QLabel(f"{self.bbox_width} px")
        self.width_label.setFixedWidth(50)
        self.width_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.width_label.setStyleSheet("""
            font-weight: 600; 
            font-size: 10px;
            background-color: #2D3748;
            border-radius: 3px;
            padding: 4px;
            border: 1px solid #A020F0;
            color: #A020F0;
        """)
        width_layout.addWidget(self.width_label)
        
        size_layout.addLayout(width_layout)
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        
        self.height_slider = CompactSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(100, 1000)
        self.height_slider.setValue(self.bbox_height)
        self.height_slider.valueChanged.connect(self.on_height_changed)
        height_layout.addWidget(self.height_slider)
        
        self.height_label = QLabel(f"{self.bbox_height} px")
        self.height_label.setFixedWidth(50)
        self.height_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.height_label.setStyleSheet("""
            font-weight: 600; 
            font-size: 10px;
            background-color: #2D3748;
            border-radius: 3px;
            padding: 4px;
            border: 1px solid #A020F0;
            color: #A020F0;
        """)
        height_layout.addWidget(self.height_label)
        
        size_layout.addLayout(height_layout)
        
        self.size_label = QLabel(f"Size: {self.bbox_width} × {self.bbox_height}")
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_label.setStyleSheet("""
            background-color: rgba(160, 32, 240, 0.1); 
            padding: 6px; 
            border-radius: 3px; 
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #A020F0;
            color: #A020F0;
        """)
        size_layout.addWidget(self.size_label)
        
        layout.addWidget(size_group)
        
        layout.addStretch()
        
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.apply_settings)
        
        self.width_slider.sliderReleased.connect(self.apply_settings_immediate)
        self.height_slider.sliderReleased.connect(self.apply_settings_immediate)
        self.width_slider.valueChanged.connect(self.schedule_save)
        self.height_slider.valueChanged.connect(self.schedule_save)
        
        self.tab_widget.addTab(tab, "Detection")
        
    def create_aim_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
    
        title_label = QLabel("Aim Settings")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 6px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
    
        # Aim Activation Button
        activation_group = CompactGroupBox("Aim Button")
        activation_layout = QVBoxLayout(activation_group)
    
        button_layout = QHBoxLayout()
        button_layout.addWidget(QLabel("Button:"))
    
        self.aim_button_combo = CompactComboBox()
        self.aim_button_combo.addItems(["BUTTON_5", "BUTTON_6", "BUTTON_7", "BUTTON_8"])
    
        current_button = self.aim_activation_button
        button_mapping = {
            "L1": "BUTTON_5", "L2": "BUTTON_6",
            "R1": "BUTTON_7", "R2": "BUTTON_8"
        }
        if current_button in button_mapping:
            current_button = button_mapping[current_button]
    
        index = self.aim_button_combo.findText(current_button)
        if index >= 0:
            self.aim_button_combo.setCurrentIndex(index)
    
        self.aim_button_combo.currentTextChanged.connect(self.on_aim_button_changed)
        button_layout.addWidget(self.aim_button_combo)
        button_layout.addStretch()
    
        activation_layout.addLayout(button_layout)
    
        self.aim_button_status = QLabel(f"Current: {current_button}")
        self.aim_button_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.aim_button_status.setStyleSheet("""
            padding: 4px; 
            background-color: rgba(160, 32, 240, 0.1); 
            border-radius: 3px; 
            font-weight: 600;
            font-size: 10px;
            border: 1px solid #A020F0;
            color: #A020F0;
        """)
        activation_layout.addWidget(self.aim_button_status)
    
        layout.addWidget(activation_group)
    
        # Offset Configuration
        offset_group = CompactGroupBox("Aim Offset")
        offset_layout = QVBoxLayout(offset_group)
    
        offset_btn = CompactButton("Open Offset Calibration", primary=True)
        offset_btn.clicked.connect(self.open_offset_window)
        offset_layout.addWidget(offset_btn)
    
        layout.addWidget(offset_group)
    
        # Aim Configuration
        aim_config_group = CompactGroupBox("Aim Config")
        aim_config_layout = QVBoxLayout(aim_config_group)
    
        aim_config_btn = CompactButton("Open Aim Configuration", primary=True)
        aim_config_btn.clicked.connect(self.open_aim_config_window)
        aim_config_layout.addWidget(aim_config_btn)
    
        layout.addWidget(aim_config_group)
    
        layout.addStretch()
    
        self.tab_widget.addTab(tab, "Aim")
    
    def on_aim_button_changed(self, button_name):
        """Handle aim activation button selection change"""
        self.aim_activation_button = button_name
        self.aim_button_status.setText(f"Current: {button_name}")
        self.save_aim_button_setting()
        self.schedule_auto_save()
    
    def save_aim_button_setting(self):
        """Save aim activation button to settings.py"""
        try:
            with open("settings.py", 'r') as f:
                lines = f.readlines()
        
            new_lines = []
            aim_button_found = False
        
            for line in lines:
                stripped_line = line.strip()
            
                if not stripped_line:
                    new_lines.append(line)
                    continue
                
                if stripped_line.startswith('aimActivationButton'):
                    if not aim_button_found:
                        new_lines.append(f'aimActivationButton = "{self.aim_activation_button}"\n')
                        aim_button_found = True
                    continue
                
                else:
                    new_lines.append(line)
        
            if not aim_button_found:
                new_lines.append(f'aimActivationButton = "{self.aim_activation_button}"\n')
        
            with open("settings.py", 'w') as f:
                f.writelines(new_lines)
            
            print(f"Saved aim button: {self.aim_activation_button}")
        
        except Exception as e:
            print(f"Error saving aim button: {e}")
    
    def create_pxd_tab(self):
        """Create the PXD Manager tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title_label = QLabel("PXD & Weights")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 13px; 
            font-weight: 600; 
            color: #A020F0; 
            padding: 6px;
            background-color: #2D3748;
            border-radius: 4px;
        """)
        layout.addWidget(title_label)
        
        # PXD File Selection
        pxd_group = CompactGroupBox("PXD Files")
        pxd_layout = QVBoxLayout(pxd_group)
        pxd_layout.setSpacing(8)
        
        # Only show currently loaded file
        self.pxd_status_label = QLabel("No PXD file loaded")
        self.pxd_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pxd_status_label.setStyleSheet("""
            padding: 6px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #4A5568;
            color: #CBD5E0;
        """)
        pxd_layout.addWidget(self.pxd_status_label)
        
        self.pxd_load_btn = CompactButton("Load PXD File", primary=True)
        self.pxd_load_btn.clicked.connect(self.toggle_pxd_load)
        pxd_layout.addWidget(self.pxd_load_btn)
        
        layout.addWidget(pxd_group)
        
        # Weights File Selection
        weights_group = CompactGroupBox("Weights Files")
        weights_layout = QVBoxLayout(weights_group)
        weights_layout.setSpacing(8)
        
        # Only show currently loaded file
        self.weights_status_label = QLabel("No Weights file loaded")
        self.weights_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weights_status_label.setStyleSheet("""
            padding: 6px; 
            background-color: #2D3748; 
            border-radius: 4px; 
            font-weight: 600;
            font-size: 11px;
            border: 1px solid #4A5568;
            color: #CBD5E0;
        """)
        weights_layout.addWidget(self.weights_status_label)
        
        self.weights_load_btn = CompactButton("Load Weights File", primary=True)
        self.weights_load_btn.clicked.connect(self.toggle_weights_load)
        weights_layout.addWidget(self.weights_load_btn)
        
        layout.addWidget(weights_group)
        
        # Refresh buttons
        refresh_layout = QHBoxLayout()
        refresh_pxd_btn = CompactButton("Refresh PXD", size="small")
        refresh_pxd_btn.clicked.connect(self.refresh_pxd_files)
        refresh_layout.addWidget(refresh_pxd_btn)
        
        refresh_weights_btn = CompactButton("Refresh Weights", size="small")
        refresh_weights_btn.clicked.connect(self.refresh_weights_files)
        refresh_layout.addWidget(refresh_weights_btn)
        
        layout.addLayout(refresh_layout)
        
        layout.addStretch()
        
        self.update_pxd_ui_state()
        self.update_weights_ui_state()
        
        self.tab_widget.addTab(tab, "PXD Manager")
    
    def load_pxd_files(self):
        """Load PXD files into the dropdown"""
        # Removed file selection dropdown as requested
        pass
    
    def load_weights_files(self):
        """Load Weights files into the dropdown"""
        # Removed file selection dropdown as requested
        pass
    
    def refresh_pxd_files(self):
        """Refresh the PXD files list"""
        # Show file dialog to select PXD file
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select PXD File", 
            self.pxd_manager.pxd_directory, 
            "PXD Files (*.pxd)"
        )
        if file_path:
            filename = os.path.basename(file_path)
            self.pxd_manager.current_pxd_file = filename
            self.load_pxd_file()
    
    def refresh_weights_files(self):
        """Refresh the Weights files list"""
        # Show file dialog to select Weights file
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Weights File", 
            self.pxd_manager.weights_directory, 
            "Weights Files (*.pt *.pth *.weights *.onnx *.bin)"
        )
        if file_path:
            filename = os.path.basename(file_path)
            self.pxd_manager.current_weights_file = filename
            self.load_weights_file()
    
    def toggle_pxd_load(self):
        """Toggle between loading and unloading PXD file"""
        if not self.pxd_manager.is_pxd_loaded:
            if not self.pxd_manager.current_pxd_file:
                self.refresh_pxd_files()
                return
            self.load_pxd_file()
        else:
            self.unload_pxd_file()
    
    def toggle_weights_load(self):
        """Toggle between loading and unloading Weights file"""
        if not self.pxd_manager.is_weights_loaded:
            if not self.pxd_manager.current_weights_file:
                self.refresh_weights_files()
                return
            self.load_weights_file()
        else:
            self.unload_weights_file()
    
    def load_pxd_file(self):
        """Load the selected PXD file"""
        if not self.pxd_manager.current_pxd_file:
            QMessageBox.warning(self, "No File", "Select a PXD file first.")
            return
        
        success, message = self.pxd_manager.load_pxd_file(self.pxd_manager.current_pxd_file)
        
        if success:
            self.update_pxd_ui_state()
            QMessageBox.information(self, "Success", f"Loaded: {self.pxd_manager.current_pxd_file}")
        else:
            QMessageBox.critical(self, "Error", message)
    
    def load_weights_file(self):
        """Load the selected Weights file"""
        if not self.pxd_manager.current_weights_file:
            QMessageBox.warning(self, "No File", "Select a Weights file first.")
            return
        
        success, message = self.pxd_manager.load_weights_file(self.pxd_manager.current_weights_file)
        
        if success:
            self.update_weights_ui_state()
            QMessageBox.information(self, "Success", f"Loaded: {self.pxd_manager.current_weights_file}")
        else:
            QMessageBox.critical(self, "Error", message)
    
    def unload_pxd_file(self):
        """Unload the current PXD file"""
        success, message = self.pxd_manager.unload_pxd_file()
        
        if success:
            self.update_pxd_ui_state()
            QMessageBox.information(self, "Success", "PXD file unloaded")
    
    def unload_weights_file(self):
        """Unload the current Weights file"""
        success, message = self.pxd_manager.unload_weights_file()
        
        if success:
            self.update_weights_ui_state()
            QMessageBox.information(self, "Success", "Weights file unloaded")
    
    def update_pxd_ui_state(self):
        """Update the UI to reflect the current PXD state"""
        if self.pxd_manager.is_pxd_loaded and self.pxd_manager.current_pxd_file:
            self.pxd_status_label.setText(f"Loaded: {self.pxd_manager.current_pxd_file}")
            self.pxd_status_label.setStyleSheet("""
                padding: 6px; 
                background-color: rgba(160, 32, 240, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                border: 1px solid #A020F0;
                font-size: 11px;
            """)
            
            self.pxd_load_btn.setText("Unload PXD")
            self.pxd_load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8A00FF;
                    color: white;
                    font-weight: 600;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #7A00E0;
                }
                QPushButton:pressed {
                    background-color: #6A00C0;
                }
            """)
        else:
            self.pxd_load_btn.setText("Load PXD")
            self.pxd_load_btn.setStyleSheet("""
                QPushButton {
                    background: #A020F0;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #8A00FF;
                }
                QPushButton:pressed {
                    background: #7A00E0;
                }
            """)
            
            self.pxd_status_label.setText("No PXD file loaded")
            self.pxd_status_label.setStyleSheet("""
                padding: 6px; 
                background-color: #2D3748; 
                border-radius: 4px; 
                font-weight: 600;
                border: 1px solid #4A5568;
                font-size: 11px;
                color: #CBD5E0;
            """)
    
    def update_weights_ui_state(self):
        """Update the UI to reflect the current Weights state"""
        if self.pxd_manager.is_weights_loaded and self.pxd_manager.current_weights_file:
            self.weights_status_label.setText(f"Loaded: {self.pxd_manager.current_weights_file}")
            self.weights_status_label.setStyleSheet("""
                padding: 6px; 
                background-color: rgba(160, 32, 240, 0.1); 
                color: #E2E8F0; 
                border-radius: 4px; 
                font-weight: 600;
                border: 1px solid #A020F0;
                font-size: 11px;
            """)
            
            self.weights_load_btn.setText("Unload Weights")
            self.weights_load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8A00FF;
                    color: white;
                    font-weight: 600;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #7A00E0;
                }
                QPushButton:pressed {
                    background-color: #6A00C0;
                }
            """)
        else:
            self.weights_load_btn.setText("Load Weights")
            self.weights_load_btn.setStyleSheet("""
                QPushButton {
                    background: #A020F0;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #8A00FF;
                }
                QPushButton:pressed {
                    background: #7A00E0;
                }
            """)
            
            self.weights_status_label.setText("No Weights file loaded")
            self.weights_status_label.setStyleSheet("""
                padding: 6px; 
                background-color: #2D3748; 
                border-radius: 4px; 
                font-weight: 600;
                border: 1px solid #4A5568;
                font-size: 11px;
                color: #CBD5E0;
            """)
    
    def open_offset_window(self):
        self.offset_window = OffsetWindow(self)
        self.offset_window.show()
        
    def open_aim_config_window(self):
        self.aim_config_window = AimConfigWindow(self)
        self.aim_config_window.show()
        
    def load_current_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                content = f.read()
            
            width_match = re.search(r'boundingBoxWidth\s*=\s*(\d+)', content)
            if width_match:
                self.bbox_width = int(width_match.group(1))
            else:
                self.bbox_width = 720
            
            height_match = re.search(r'boundingBoxHeight\s*=\s*(\d+)', content)
            if height_match:
                self.bbox_height = int(height_match.group(1))
            else:
                self.bbox_height = 480
            
            aim_button_match = re.search(r'aimActivationButton\s*=\s*"([^"]+)"', content)
            if aim_button_match:
                self.aim_activation_button = aim_button_match.group(1)
            else:
                self.aim_activation_button = "BUTTON_7"
                
            self.last_saved_values = (self.bbox_width, self.bbox_height)
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.bbox_width = 720
            self.bbox_height = 480
            self.aim_activation_button = "BUTTON_7"
            self.last_saved_values = (720, 480)
        
    def on_width_changed(self, value):
        self.bbox_width = value
        self.width_label.setText(f"{value} px")
        self.size_label.setText(f"Size: {self.bbox_width} × {self.bbox_height}")
        self.schedule_auto_save()
        
    def on_height_changed(self, value):
        self.bbox_height = value
        self.height_label.setText(f"{value} px")
        self.size_label.setText(f"Size: {self.bbox_width} × {self.bbox_height}")
        self.schedule_auto_save()
        
    def schedule_save(self):
        self.save_timer.start(100)
        self.schedule_auto_save()
        
    def apply_settings_immediate(self):
        self.save_timer.stop()
        self.apply_settings()
        self.schedule_auto_save()
        
    def apply_settings(self):
        current_values = (self.bbox_width, self.bbox_height)
        
        if current_values != self.last_saved_values:
            try:
                with open(self.settings_file, 'r') as f:
                    content = f.read()
                
                content = re.sub(
                    r'boundingBoxWidth\s*=\s*\d+', 
                    f'boundingBoxWidth = {self.bbox_width}', 
                    content
                )
                
                content = re.sub(
                    r'boundingBoxHeight\s*=\s*\d+', 
                    f'boundingBoxHeight = {self.bbox_height}', 
                    content
                )
                
                with open(self.settings_file, 'w') as f:
                    f.write(content)
                
                self.last_saved_values = current_values
                print(f"Saved: {self.bbox_width}x{self.bbox_height}")
                
            except Exception as e:
                print(f"Error saving: {e}")

def launch_gui():
    try:
        app = QApplication(sys.argv)
        
        # Create and show splash screen
        splash = SplashScreen()
        splash.show()
        app.processEvents()
        time.sleep(1)
        
        # Set application-wide font
        font = QFont("Segoe UI", 9)
        app.setFont(font)
        
        # Create and show main window
        gui = F4VisionSettingsGUI()
        
        # Close splash and show main window
        splash.finish(gui)
        gui.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error launching GUI: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    launch_gui()