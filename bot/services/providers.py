from enum import Enum


class Provider(str, Enum):
    KBZPAY = "kbzpay"
    WAVEPAY = "wavepay"
