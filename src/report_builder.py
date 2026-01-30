# =========================
# src/report_builder.py
# =========================
class ReportBuilder:
    @staticmethod
    def build(profile: dict, analysis: dict) -> str:
        pa = analysis["price_action"]

        if pa["allow_trade"]:
            decision_line = f"✅ 允许交易：{pa['signal']['type']}"
        else:
            decision_line = "🚫 当前不可交易（仅研究备忘）"

        return f"""
🎯 {profile['code']}（{profile['name']}）

📌 技术裁决（Price Action）
{decision_line}

原因：
{pa['reason']}

说明：
本结论基于价格行为系统判断。
若不可交易，仅用于研究与跟踪，不构成交易建议。
"""