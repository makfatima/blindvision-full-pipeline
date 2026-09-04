# Hardware Architecture & Bill of Materials — BlindVision

## System Overview

BlindVision uses a dual-device architecture consisting of Smart Goggles for wearable vision and a Smart Stick for independent ground-level sensing. The two devices exchange structured sensor packets over BLE, while the goggles provide the edge-computing platform for on-device YOLOv8 inference.

## Smart Goggles (Vision Node)

| Component | Model / specification | Function |
|---|---|---|
| Edge computer | Raspberry Pi 4 Model B, 4 GB RAM | On-device computer-vision inference and sensor fusion |
| Cameras | Four wide-angle USB cameras, 1080p, 120° FOV | Visual obstacle detection and directional coverage |
| Vision model | YOLOv8n | On-device object detection |
| GNSS | u-blox NEO-6M | Outdoor position / caregiver geofencing |
| Cellular | SIM800L GSM/GPRS | Caregiver/backend communication fallback |
| Audio | Bluetooth earbud with backup speaker/buzzer | Voice alerts |
| Storage | 64 GB microSDXC | Operating system, models, and logs |
| Power | 10,000 mAh USB power bank | Goggles power source |

## Smart Stick (Ground Node)

| Component | Model / specification | Function |
|---|---|---|
| Microcontroller | ESP32 DevKit V1 | Sensor acquisition, local safety logic, and BLE |
| Ultrasonic sensors | Five ultrasonic rangers | Ground and obstacle-distance sensing |
| IR sensors | Two downward IR proximity sensors | Edge and stair detection |
| Water sensor | Resistive water-level sensor | Water-surface hazard detection |
| IMU | MPU9250 | Fall and knock sensing |
| Force sensor | Tip-mounted force-sensitive resistor (FSR) | Ground-contact confirmation |
| Emergency input | Handle-mounted SOS pushbutton | Emergency alert |
| Outputs | Vibration motor, piezo buzzer, LED safety light | Haptic, audio, and visual feedback |
| Battery | 3.7 V nominal, 5000 mAh 18650 Li-ion cell | Smart Stick power source |
| Charger | TP4056 | Battery charging |

## Communication and Power Domains

The Stick streams structured sensor/status packets to the Goggles over BLE. The Goggles use a separate 10,000 mAh USB power bank, while the Stick uses its separate 3.7 V nominal 5000 mAh cell. Power measurements must therefore be interpreted by device and power domain rather than as one common battery voltage.

## GPIO Configuration

The released hardware description does not claim a complete pin map unless the corresponding as-built firmware configuration is present in the release. Pin assignments should therefore be taken directly from the released firmware source rather than inferred from component defaults.
