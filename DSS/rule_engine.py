"""
rule_engine.py — PLACEHOLDER (skeleton only)

Ban goc: OmniSenseRuleEngine - rule-based layer xu ly canh bao/hanh dong
song song voi AI Core (KMeans). Da luoc bo phan logic rule chi tiet vi ly
do bao mat chat xam, chi giu lai khung class/method de code khac import
khong bi loi.
"""


class OmniSenseRuleEngine:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def trigger_action(self, entity_id, action_name, priority, cooldown_hours=24):
        """[PLACEHOLDER] Kich hoat 1 hanh dong, co cooldown de tranh spam."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def _dispatch_event(self, channel, payload):
        """[PLACEHOLDER] Publish event qua Redis channel."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def process_delivery_rules(self, row):
        """[PLACEHOLDER] Danh gia rule lien quan risk giao hang."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    def process_churn_rules(self, row):
        """[PLACEHOLDER] Danh gia rule lien quan churn khach hang."""
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")
