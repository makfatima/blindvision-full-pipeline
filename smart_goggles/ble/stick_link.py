"""
BLE central on the Raspberry Pi's built-in Bluetooth radio, receiving the
Smart Stick's structured sensor packet (Section III). Because the stick's
ESP32-WROOM-32 module implements Bluetooth 4.2, the link operates at 4.2
rather than 5.0.

Packet format (little-endian, matches smart_stick/ble_peripheral.cpp):

    struct SensorPacket {
        uint32_t seq;              // monotonically increasing sequence number
        uint16_t us_front_cm;      // 0xFFFF = no echo / out of range
        uint16_t us_left_cm;
        uint16_t us_right_cm;
        uint16_t us_rear_cm;
        uint16_t us_down_cm;       // downward-angled transducer (drop-off)
        uint16_t ir_edge_cm;       // downward IR (edge/stair)
        uint8_t  down_no_return;   // 0/1 -- nothing heard below (drop-off/void)
        uint8_t  ir_ground_absent; // 0/1 -- no IR ground return
        uint8_t  water_detected;   // 0/1
        uint8_t  fall_detected;    // 0/1
        uint8_t  sos_pressed;      // 0/1
        uint8_t  fsr_contact;      // 0/1 (ground contact confirmed)
        uint8_t  battery_pct;      // 0-100
        int16_t  imu_pitch_deg_x10;
        int16_t  imu_roll_deg_x10;
        uint32_t echo_token;       // last ping token the stick saw; 0 if none
    }  # 31 bytes; asserted against struct.calcsize() below
"""

import asyncio
import logging
import struct
import time
from dataclasses import dataclass
from typing import Callable, Optional

from config import DROPOFF_DOWN_DISTANCE_M, BLE_STICK_COMMAND_CHAR_UUID

logger = logging.getLogger("blindvision.ble")

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover
    BleakClient = None
    BleakScanner = None

_PACKET_FORMAT = "<IHHHHHHBBBBBBBhhI"
_PACKET_SIZE = struct.calcsize(_PACKET_FORMAT)
assert _PACKET_SIZE == 31, f"packet layout drifted: {_PACKET_SIZE} != 31"

# Written to the stick's RX characteristic to start a round-trip measurement.
PING_PREFIX = "ping:"


@dataclass
class StickPacket:
    seq: int
    us_front_m: Optional[float]
    us_left_m: Optional[float]
    us_right_m: Optional[float]
    us_rear_m: Optional[float]
    us_down_m: Optional[float]
    ir_edge_m: Optional[float]
    down_no_return: bool
    ir_ground_absent: bool
    water_detected: bool
    fall_detected: bool
    sos_pressed: bool
    fsr_contact: bool
    battery_pct: int
    imu_pitch_deg: float
    imu_roll_deg: float
    echo_token: int
    received_at: float
    received_perf: float

    @property
    def nearest_ultrasonic_m(self) -> Optional[float]:
        vals = [v for v in (self.us_front_m, self.us_left_m,
                             self.us_right_m, self.us_rear_m) if v is not None]
        return min(vals) if vals else None

    @property
    def drop_off_detected(self) -> bool:
        """Algorithm 1 tier 2. Three signatures, any of which means there is
        no ground where there should be:

          1. the downward transducer heard nothing at all (void below, or an
             absorbing surface) -- `down_no_return`;
          2. neither IR sensor sees a ground return -- `ir_ground_absent`;
          3. a *measured* down-distance past the nominal ground plane.

        Signatures 1 and 2 were previously discarded: no-echo became the
        0xFFFF sentinel, which parsed to None, which failed the ">0.5 m"
        comparison, so the strongest drop-off case produced no alert.
        """
        if self.down_no_return or self.ir_ground_absent:
            return True
        return (self.us_down_m is not None
                and self.us_down_m > DROPOFF_DOWN_DISTANCE_M)

    @property
    def down_distance_m(self) -> Optional[float]:
        """Measured downward distance, or None if nothing was heard. Callers
        wanting drop-off *state* should use `drop_off_detected`, which also
        covers the no-return cases this property cannot express."""
        return self.us_down_m


def _cm_to_m(raw: int) -> Optional[float]:
    if raw == 0xFFFF:
        return None
    return raw / 100.0


def parse_packet(raw: bytes) -> StickPacket:
    if len(raw) != _PACKET_SIZE:
        raise ValueError(f"Unexpected packet size: {len(raw)} != {_PACKET_SIZE}")
    (seq, us_f, us_l, us_r, us_re, us_d, ir_e, down_nr, ir_absent,
     water, fall, sos, fsr, batt, pitch10, roll10, echo_token) = struct.unpack(
        _PACKET_FORMAT, raw)
    return StickPacket(
        seq=seq,
        us_front_m=_cm_to_m(us_f),
        us_left_m=_cm_to_m(us_l),
        us_right_m=_cm_to_m(us_r),
        us_rear_m=_cm_to_m(us_re),
        us_down_m=_cm_to_m(us_d),
        ir_edge_m=_cm_to_m(ir_e),
        down_no_return=bool(down_nr),
        ir_ground_absent=bool(ir_absent),
        water_detected=bool(water),
        fall_detected=bool(fall),
        sos_pressed=bool(sos),
        fsr_contact=bool(fsr),
        battery_pct=batt,
        imu_pitch_deg=pitch10 / 10.0,
        imu_roll_deg=roll10 / 10.0,
        echo_token=echo_token,
        received_at=time.time(),
        received_perf=time.perf_counter(),
    )


class StickLink:
    """Manages connection lifecycle and packet delivery from the Smart Stick."""

    def __init__(self, service_uuid: str, char_uuid: str,
                 device_name_prefix: str = "BlindVision-Stick",
                 link_timeout_s: float = 5.0,
                 command_char_uuid: Optional[str] = None):
        self.service_uuid = service_uuid
        self.char_uuid = char_uuid
        # Write characteristic, used for ping tokens in the current release.
        self.command_char_uuid = command_char_uuid or BLE_STICK_COMMAND_CHAR_UUID
        self.device_name_prefix = device_name_prefix
        self.link_timeout_s = link_timeout_s
        self._client: Optional["BleakClient"] = None
        self.last_packet: Optional[StickPacket] = None
        self.last_packet_time: float = 0.0

        # Link-reliability accounting. The stick stamps every packet with a
        # monotonic `seq`; the gap between consecutive sequence numbers is
        # the number of packets that did not arrive. Without this the
        # firmware emits `seq` and nothing ever reads it, so no delivery
        # figure can be produced from a run at all.
        self.packets_received: int = 0
        self.packets_expected: int = 0
        self.packets_lost: int = 0
        self.malformed_packets: int = 0
        self._last_seq: Optional[int] = None

        # BLE round-trip measurement. The two devices have unsynchronised
        # clocks, so a one-way delay cannot be measured from this side at
        # all. What can be measured is: write a token, wait for the stick to
        # echo it in a notify, take the difference on ONE clock.
        self._ping_token: int = 0
        self._ping_sent_perf: Optional[float] = None
        self.last_rtt_ms: Optional[float] = None
        self.rtt_samples: list = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def delivery_rate(self) -> Optional[float]:
        """Observed packet delivery rate over this connection, or None
        before any packet has arrived. This is the quantity a reported BLE
        reliability figure has to come from."""
        if self.packets_expected == 0:
            return None
        return self.packets_received / self.packets_expected

    async def measure_rtt(self, timeout_s: float = 2.0) -> Optional[float]:
        """Write a ping token and wait for the stick to echo it back.

        Returns the round trip in milliseconds, or None on timeout. The
        one-way component is RTT/2 and must be labelled DERIVED wherever it
        appears -- it assumes a symmetric path, which a BLE connection
        interval does not guarantee.
        """
        if self._client is None or not self._client.is_connected:
            return None
        self._ping_token = (self._ping_token + 1) & 0x7FFFFFFF or 1
        token = self._ping_token
        self._ping_sent_perf = time.perf_counter()
        await self._client.write_gatt_char(
            self.command_char_uuid, f"{PING_PREFIX}{token}".encode())

        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            packet = self.last_packet
            if packet is not None and packet.echo_token == token:
                rtt_ms = (packet.received_perf - self._ping_sent_perf) * 1000.0
                self.last_rtt_ms = rtt_ms
                self.rtt_samples.append(rtt_ms)
                return rtt_ms
            await asyncio.sleep(0.005)
        logger.warning("BLE ping %d not echoed within %.1fs", token, timeout_s)
        return None

    def reset_link_stats(self):
        self.packets_received = 0
        self.packets_expected = 0
        self.packets_lost = 0
        self.malformed_packets = 0
        self._last_seq = None

    def _account(self, seq: int):
        self.packets_received += 1
        if self._last_seq is None:
            self.packets_expected += 1
        else:
            delta = (seq - self._last_seq) & 0xFFFFFFFF
            if delta == 0:
                self.packets_received -= 1  # duplicate, not a new packet
                return
            self.packets_expected += delta
            self.packets_lost += delta - 1
        self._last_seq = seq

    @property
    def is_stale(self) -> bool:
        """True once no packet has arrived within link_timeout_s -- the
        trigger condition for falling back to Vision-Only Mode (Section III)."""
        if self.last_packet_time == 0.0:
            return True
        return (time.time() - self.last_packet_time) > self.link_timeout_s

    async def connect(self, on_packet: Callable[[StickPacket], None]):
        self._loop = asyncio.get_running_loop()
        if BleakScanner is None:
            raise RuntimeError("bleak is required: pip install bleak")

        device = await BleakScanner.find_device_by_filter(
            lambda d, adv: d.name is not None and d.name.startswith(self.device_name_prefix)
        )
        if device is None:
            raise RuntimeError("Smart Stick not found -- ensure it is powered and advertising")

        self._client = BleakClient(device)
        await self._client.connect()
        logger.info("Connected to Smart Stick at %s", device.address)

        def _handle_notify(_char, data: bytearray):
            try:
                packet = parse_packet(bytes(data))
            except ValueError as exc:
                self.malformed_packets += 1
                logger.warning("Dropped malformed stick packet: %s", exc)
                return
            self._account(packet.seq)
            self.last_packet = packet
            self.last_packet_time = packet.received_at
            on_packet(packet)

        await self._client.start_notify(self.char_uuid, _handle_notify)

    async def disconnect(self):
        if self._client and self._client.is_connected:
            await self._client.disconnect()


async def run_stick_link(link: StickLink, on_packet: Callable[[StickPacket], None]):
    """Reconnect loop -- keeps trying if the stick drops out, while the
    caller's mode manager independently watches `link.is_stale` for the
    5-second Vision-Only fallback."""
    while True:
        try:
            await link.connect(on_packet)
            while link._client and link._client.is_connected:
                await asyncio.sleep(1.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stick BLE link error: %s -- retrying in 2s", exc)
            await asyncio.sleep(2.0)
