#include "ble_peripheral.h"
#include "config.h"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

static BLEServer* pServer = nullptr;
static BLECharacteristic* pTxChar = nullptr;
static BLECharacteristic* pRxChar = nullptr;
static bool deviceConnected = false;

// Latency instrumentation: the goggles write "ping:<uint32>" and the stick
// echoes that token in every subsequent notify until a new one arrives. The
// goggles can then measure a real BLE round trip. The two devices do not
// share a clock, so a round trip is the only thing that CAN be measured from
// one side; the one-way component is derived, never claimed as measured.
static uint32_t lastEchoToken = 0;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* server) override { deviceConnected = true; }
  void onDisconnect(BLEServer* server) override {
    deviceConnected = false;
    server->getAdvertising()->start();  // resume advertising after disconnect
  }
};

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    std::string value = characteristic->getValue();
    if (value.empty()) return;
    if (value.rfind("ping:", 0) == 0) {
      lastEchoToken = (uint32_t) strtoul(value.substr(5).c_str(), nullptr, 10);
      return;   // not a haptic command
    }
    // Non-ping writes are retained as an unused integration point; the
    // current goggles release does not send remote haptic commands.
  }
};

void ble_peripheral_init() {
  BLEDevice::init(BLE_DEVICE_NAME);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService* service = pServer->createService(BLE_SERVICE_UUID);

  pTxChar = service->createCharacteristic(
      BLE_CHAR_TX_UUID,
      BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
  pTxChar->addDescriptor(new BLE2902());

  pRxChar = service->createCharacteristic(
      BLE_CHAR_RX_UUID,
      BLECharacteristic::PROPERTY_WRITE);
  pRxChar->setCallbacks(new RxCallbacks());

  service->start();

  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_SERVICE_UUID);
  advertising->setScanResponse(true);
  BLEDevice::startAdvertising();
}

bool ble_peripheral_is_connected() {
  return deviceConnected;
}

// Must match the little-endian struct layout documented in
// smart_goggles/ble/stick_link.py (_PACKET_FORMAT = "<IHHHHHHBBBBBBBhhI").
// 31 bytes. Verify with struct.calcsize() on the Python side and
// sizeof(WirePacket) here -- the two must agree exactly.
struct __attribute__((packed)) WirePacket {
  uint32_t seq;
  uint16_t us_front_cm;
  uint16_t us_left_cm;
  uint16_t us_right_cm;
  uint16_t us_rear_cm;
  uint16_t us_down_cm;
  uint16_t ir_edge_cm;
  uint8_t  down_no_return;
  uint8_t  ir_ground_absent;
  uint8_t  water_detected;
  uint8_t  fall_detected;
  uint8_t  sos_pressed;
  uint8_t  fsr_contact;
  uint8_t  battery_pct;
  int16_t  imu_pitch_deg_x10;
  int16_t  imu_roll_deg_x10;
  uint32_t echo_token;   // last ping token seen; 0 if none
};

void ble_peripheral_send_snapshot(const SensorSnapshot& snapshot, uint32_t seq) {
  if (!deviceConnected || pTxChar == nullptr) return;

  WirePacket pkt{};
  pkt.seq = seq;
  pkt.us_front_cm = snapshot.us_front_cm;
  pkt.us_left_cm = snapshot.us_left_cm;
  pkt.us_right_cm = snapshot.us_right_cm;
  pkt.us_rear_cm = snapshot.us_rear_cm;
  pkt.us_down_cm = snapshot.us_down_cm;
  pkt.ir_edge_cm = snapshot.ir_edge_cm;
  pkt.down_no_return = snapshot.down_no_return ? 1 : 0;
  pkt.ir_ground_absent = snapshot.ir_ground_absent ? 1 : 0;
  pkt.water_detected = snapshot.water_detected ? 1 : 0;
  pkt.fall_detected = snapshot.fall_detected ? 1 : 0;
  pkt.sos_pressed = snapshot.sos_pressed ? 1 : 0;
  pkt.fsr_contact = snapshot.fsr_contact ? 1 : 0;
  pkt.battery_pct = snapshot.battery_pct;
  pkt.imu_pitch_deg_x10 = (int16_t) (snapshot.imu_pitch_deg * 10.0f);
  pkt.imu_roll_deg_x10 = (int16_t) (snapshot.imu_roll_deg * 10.0f);
  pkt.echo_token = lastEchoToken;

  pTxChar->setValue((uint8_t*) &pkt, sizeof(WirePacket));
  pTxChar->notify();
}

