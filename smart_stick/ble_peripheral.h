/*
 * BLE peripheral (GATT server) exposing the Smart Stick's sensor packet to
 * the Smart Goggles' BLE central (Bluetooth 4.2, per the ESP32-WROOM-32
 * module -- Section III). Core 1 manages the BLE stack and state machine.
 */

#ifndef BLINDVISION_STICK_BLE_PERIPHERAL_H
#define BLINDVISION_STICK_BLE_PERIPHERAL_H

#include "sensors.h"

void ble_peripheral_init();
bool ble_peripheral_is_connected();

// Serializes a SensorSnapshot into the 24-byte packet format documented in
// smart_goggles/ble/stick_link.py and sends it as a BLE notification.
void ble_peripheral_send_snapshot(const SensorSnapshot& snapshot, uint32_t seq);

// The RX characteristic is reserved for ping tokens in the current release;
// remote haptic writes are not exercised by the goggles.

#endif  // BLINDVISION_STICK_BLE_PERIPHERAL_H
