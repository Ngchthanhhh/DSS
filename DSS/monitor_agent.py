"""
monitor_agent.py — PLACEHOLDER (skeleton only)

Ban goc: service chay nen, load model (XGBoost/RandomForest) + query
Postgres qua rule_engine de phat hien risk/churn theo thoi gian thuc,
publish canh bao qua Redis. Da luoc bo logic SQL/rule chi tiet va viec
load model (.pkl khong duoc dinh kem trong ban rut gon nay) vi ly do
bao mat chat xam.
"""


def load_models():
    """[PLACEHOLDER] Load model XGBoost (delivery risk) va RandomForest (churn) tu .pkl."""
    raise NotImplementedError("Model .pkl khong duoc dinh kem. Xem source goc cua chu repo.")


def get_delivery_risk_count():
    """[PLACEHOLDER] Query + predict so luong don hang co risk giao hang cao."""
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")


def get_churn_count():
    """[PLACEHOLDER] Query + predict so luong khach hang co nguy co churn."""
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")


def scan_and_publish():
    """[PLACEHOLDER] Vong lap chinh: quet dinh ky va publish canh bao qua Redis."""
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")


if __name__ == "__main__":
    print("Day la ban skeleton, khong the chay truc tiep. Lien he chu repo de lay ban day du.")
