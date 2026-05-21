#!/usr/bin/env python3
import time
import serial

PORT = "/dev/ttyUSB5"
BAUDRATE = 9600
TIMEOUT = 2
SLAVE = 1


def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder="little")


def read_register(reg, signed=False, scale=1, name=""):
    frame = bytes([
        SLAVE,
        0x03,
        (reg >> 8) & 0xFF,
        reg & 0xFF,
        0x00,
        0x01
    ])
    frame += crc16_modbus(frame)

    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="E",
        stopbits=1,
        timeout=TIMEOUT
    ) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("\n--------------------------------")
        print(f"REG {reg} | {name}")
        print("TX:", frame.hex(" ").upper())

        ser.write(frame)
        time.sleep(1)

        rx = ser.read(100)
        print("RX:", rx.hex(" ").upper() if rx else "TIMEOUT")

    if not rx:
        return None

    if len(rx) >= 3 and rx[1] & 0x80:
        print(f"EXCEPCIÓN MODBUS: código {rx[2]}")
        return None

    if len(rx) < 7:
        print("Respuesta incompleta")
        return None

    raw = int.from_bytes(rx[3:5], byteorder="big", signed=signed)
    value = raw / scale

    print(f"RAW: {raw}")
    print(f"VALOR: {value}")

    return value


def main():
    print("\n=== SCAN SOLO LECTURA SAMSUNG MIM-B19N ===")
    print(f"Puerto: {PORT}")
    print("Serial: 9600,E,8,1")
    print("Slave : 1")

    registers = [
        (50, False, 1,  "Communication status IU0"),
        (51, False, 1,  "Unit type IU0"),
        (52, False, 1,  "Air conditioner ON/OFF"),
        (53, False, 1,  "Operating mode"),
        (54, False, 1,  "Indoor fan speed"),
        (57, True,  10, "Set temperature °C"),
        (58, True,  10, "Room temperature °C"),
        (63, False, 1,  "Indoor unit error code"),
    ]

    for reg, signed, scale, name in registers:
        read_register(reg, signed=signed, scale=scale, name=name)
        time.sleep(0.5)


if __name__ == "__main__":
    main()