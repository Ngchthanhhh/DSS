"""
agents/retention_agent.py — PLACEHOLDER (skeleton only)

Ban goc: PrivacyAgent (mask/anonymize du lieu khach hang) + RetentionAgent
(sinh email winback qua LLM). Da luoc bo logic chi tiet vi ly do bao mat
chat xam va thong tin ca nhan.
"""


class PrivacyAgent:
    def __init__(self):
        pass

    def mask_email(self, email):
        """[PLACEHOLDER] Che mot phan email de bao mat."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def mask_name(self, name):
        """[PLACEHOLDER] Che mot phan ten khach hang."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def anonymize_customer_data(self, customer_data):
        """[PLACEHOLDER] Anonymize toan bo record khach hang."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")


class RetentionAgent:
    def __init__(self):
        pass

    def generate_winback_email(self, raw_customer_data, churn_reason, voucher_code="COMEBACK20"):
        """[PLACEHOLDER] Sinh noi dung email winback ca nhan hoa qua LLM."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def _fallback_template(self, safe_data, safe_name, churn_reason, voucher_code):
        """[PLACEHOLDER] Template du phong khi LLM loi."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")
